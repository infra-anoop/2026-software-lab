"""`shell-guard` (beforeShellExecution; CI twin `branch-protection-require-pr`).

Denies, for every actor (I-P10, contracts/hooks.md): `git commit` while the checked-out
branch is `main`; any `git push` whose destination ref is `main` (update, force or
delete, however spelled); force pushes; `pip install`; `gh workflow run`; writes to
`/etc`, `/usr` or `~/.config` outside the repo; `nix-env -i`. Each command is judged in
the repository it runs in (`cwd`, `cd`, `git -C`). Quoted or commented text never runs.
"""

from __future__ import annotations

import os.path
import re
from pathlib import Path

from factory.hooks._repo import branch_in, git_root
from factory.hooks.shell_words import SimpleCommand, simple_commands, tokenize

DENY_EXIT = 2
MAX_NESTING = 5
MAIN = "main"
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "ash", "fish"})
KEYWORDS = frozenset({"{", "}", "!", "if", "then", "do", "else", "elif", "while", "until", "time"})
WRAPPER_VALUE_OPTIONS = {
    "sudo": frozenset({"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T"}),
    "env": frozenset({"-u", "-S", "--unset", "--split-string"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "xargs": frozenset({"-I", "-n", "-P", "-d", "-L", "-s", "-a", "-E", "-i"}),
    "stdbuf": frozenset({"-i", "-o", "-e"}),
    "timeout": frozenset({"-s", "--signal", "-k", "--kill-after"}),
    "command": frozenset(),
    "exec": frozenset({"-a"}),
    "nohup": frozenset(),
}
GIT_VALUE_OPTIONS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix"}
)
PUSH_VALUE_OPTIONS = frozenset({"--repo", "--receive-pack", "--exec", "--push-option", "-o"})
WRITE_EVERY_ARG = frozenset(
    {"tee", "mkdir", "touch", "rm", "rmdir", "truncate", "chmod", "chown", "chgrp", "unlink"}
)
WRITE_LAST_ARG = frozenset({"cp", "mv", "install", "ln", "rsync", "scp"})
PIP = re.compile(r"^pip\d*(?:\.\d+)?$")
PYTHON = re.compile(r"^python\d*(?:\.\d+)?$")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
HOME_VAR = re.compile(r"^(?:~|\$HOME|\$\{HOME\})(?=/|$)")

GUIDANCE = {
    "main": "Commit on a wo/<order-id> branch and open a PR (AGENTS.md rule 11, I-P10).",
    "force": "Force pushes are not allowed; push new commits instead.",
    "pip": "Use `uv sync --locked` in the app, or Nix; no durable pip installs.",
    "workflow": "Codespace tokens cannot dispatch workflows: push a branch or a tag.",
    "nix-env": "Declare tools in flake.nix and use `nix develop`.",
    "system": "Keep writes inside the repository; system paths need the governor.",
}


class Scope:
    """Where a command runs: its working directory, the home dir, and the repo root."""

    __slots__ = ("cwd", "home", "repo_root")

    def __init__(self, cwd: str, home: str, repo_root: str | None) -> None:
        self.cwd = cwd
        self.home = home
        self.repo_root = repo_root

    def path(self, raw: str, base: str | None = None) -> str:
        expanded = HOME_VAR.sub(lambda _: self.home, raw)
        return os.path.normpath(os.path.join(base or self.cwd, expanded))


Finding = tuple[str, str]  # (guidance key, reason)


def _non_options(args: list[str]) -> list[str]:
    return [arg for arg in args if not arg.startswith("-")]


def _strip_prefixes(argv: list[str], scope: Scope) -> list[str] | None:
    """Drop assignments, shell keywords and exec wrappers; None for a lookup-only
    `command -v`."""
    args = list(argv)
    while args:
        word = args[0]
        name = os.path.basename(word)
        if word in KEYWORDS or ASSIGNMENT.match(word):
            args.pop(0)
        elif name in WRAPPER_VALUE_OPTIONS:
            args.pop(0)
            takes_value = WRAPPER_VALUE_OPTIONS[name]
            while args and (args[0].startswith("-") or (name == "env" and "=" in args[0])):
                option = args.pop(0)
                if name == "command" and option in {"-v", "-V"}:
                    return None
                if name == "env" and option in {"-C", "--chdir"} and args:
                    scope.cwd = scope.path(args.pop(0))
                elif option in takes_value and args:
                    args.pop(0)
            if name == "timeout" and args:
                args.pop(0)  # the duration
        else:
            break
    return args


def _system_path(raw: str, scope: Scope) -> str | None:
    if not raw or raw.isdigit() or raw == "-":
        return None
    path = scope.path(raw)
    for protected in ("/etc", "/usr", os.path.join(scope.home, ".config")):
        if path == protected or path.startswith(protected + "/"):
            root = scope.repo_root
            if root and (path == root or path.startswith(root.rstrip("/") + "/")):
                return None
            return path
    return None


def _write_targets(name: str, args: list[str]) -> list[str]:
    if name in WRITE_EVERY_ARG or (
        name == "sed" and any(a.startswith(("-i", "--in-place")) for a in args)
    ):
        return _non_options(args)
    if name in WRITE_LAST_ARG:
        for i, arg in enumerate(args):
            if arg in {"-t", "--target-directory"} and i + 1 < len(args):
                return [args[i + 1]]
            if arg.startswith("--target-directory="):
                return [arg.split("=", 1)[1]]
        operands = _non_options(args)
        return operands[-1:] if len(operands) > 1 else []
    if name == "dd":
        return [arg[3:] for arg in args if arg.startswith("of=")]
    return []


def _push_destinations(args: list[str], branch: str | None) -> tuple[list[str], bool, bool]:
    """(destination refs, force, pushes every branch) of `git push <args>`."""
    force = delete = every = tags_only = False
    positional: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        i += 1
        if arg == "--":
            positional += args[i:]
            break
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            force |= name in {"--force", "--force-with-lease"}
            delete |= name == "--delete"
            every |= name in {"--all", "--mirror", "--branches"}
            tags_only |= name == "--tags"
            if name in PUSH_VALUE_OPTIONS and "=" not in arg:
                i += 1
        elif arg.startswith("-") and len(arg) > 1:
            for position, flag in enumerate(arg[1:], start=1):
                force |= flag == "f"
                delete |= flag == "d"
                if flag == "o":
                    i += 0 if position < len(arg) - 1 else 1
                    break
        else:
            positional.append(arg)
    refspecs = positional[1:]
    destinations: list[str] = []
    for spec in refspecs:
        if spec.startswith("+"):
            force = True
            spec = spec[1:]
        if delete:
            destination = spec
        elif ":" in spec:
            source, destination = spec.split(":", 1)
            destination = destination or source
        else:
            destination = spec
        destinations.append(branch or "" if destination in {"HEAD", "@"} else destination)
    if not refspecs and not delete and not tags_only and branch:
        destinations.append(branch)
    return [d.removeprefix("refs/heads/") for d in destinations], force, every


def _judge_git(args: list[str], scope: Scope) -> Finding | None:
    repo_dir = scope.cwd
    git_dir: Path | None = None
    i = 0
    while i < len(args):
        arg = args[i]
        name, _, inline = arg.partition("=")
        if arg in GIT_VALUE_OPTIONS and i + 1 < len(args):
            value = args[i + 1]
            i += 2
        elif name in {"--git-dir", "--work-tree"} and inline:
            value = inline
            i += 1
        elif arg.startswith("-C") and len(arg) > 2:
            name, value = "-C", arg[2:]
            i += 1
        elif arg.startswith("-"):
            i += 1
            continue
        else:
            break
        if name in {"-C", "--work-tree"}:
            repo_dir = scope.path(value, repo_dir)
        elif name == "--git-dir":
            git_dir = Path(scope.path(value, repo_dir))
    if i >= len(args):
        return None
    subcommand, rest = args[i], args[i + 1 :]
    if subcommand not in {"commit", "push"}:
        return None
    branch = branch_in(Path(repo_dir), explicit_git_dir=git_dir)
    if subcommand == "commit":
        if branch == MAIN:
            return "main", f"`git commit` while `main` is checked out in {repo_dir}"
        return None
    destinations, force, every = _push_destinations(rest, branch)
    if force:
        return "force", "force push (`--force`, `-f`, `--force-with-lease` or a `+` refspec)"
    if every:
        return "main", "`git push --all/--mirror/--branches` also pushes `main`"
    if MAIN in destinations:
        return "main", "`git push` whose destination ref is `main`"
    return None


def _runs_pip_install(args: list[str]) -> bool:
    """`python [options] -m pip [options] install ...`; `-m` ends the interpreter options."""
    for i, arg in enumerate(args):
        if arg == "-m" and i + 1 < len(args):
            module, after = args[i + 1], args[i + 2 :]
        elif arg.startswith("-m") and len(arg) > 2:
            module, after = arg[2:], args[i + 1 :]
        elif arg.startswith("-"):
            continue
        else:
            return False
        return module == "pip" and _non_options(after)[:1] == ["install"]
    return False


def _judge_program(argv: list[str], scope: Scope, depth: int) -> Finding | None:
    stripped = _strip_prefixes(argv, scope)
    if not stripped:
        return None
    name, args = os.path.basename(stripped[0]), stripped[1:]
    if name in SHELLS:
        wants_script = False
        for arg in args:
            if arg.startswith(("-", "+")) and arg != "--":
                wants_script |= "c" in arg[1:] and not arg.startswith("--")
                continue
            return _judge_text(arg, scope, depth + 1) if wants_script else None
        return None
    if name == "eval":
        return _judge_text(" ".join(args), scope, depth + 1)
    if name == "git":
        return _judge_git(args, scope)
    operands = _non_options(args)
    if PIP.match(name) and operands[:1] == ["install"]:
        return "pip", "`pip install`"
    if PYTHON.match(name) and _runs_pip_install(args):
        return "pip", "`python -m pip install`"
    if name == "uv" and operands[:2] == ["pip", "install"]:
        return "pip", "`uv pip install`"
    if name == "gh" and operands[:2] == ["workflow", "run"]:
        return "workflow", "`gh workflow run`"
    if name == "nix-env" and any(
        a == "--install" or (re.fullmatch(r"-[A-Za-z]+", a) and "i" in a) for a in args
    ):
        return "nix-env", "`nix-env -i` (imperative profile install)"
    for target in _write_targets(name, args):
        path = _system_path(target, scope)
        if path:
            return "system", f"`{name}` writes to {path}, a system path outside the repo"
    return None


def _judge_command(command: SimpleCommand, scope: Scope, depth: int) -> Finding | None:
    for operator, target in command.redirects:
        if ">" in operator and not (operator == ">&" and (target.isdigit() or target == "-")):
            path = _system_path(target, scope)
            if path:
                return "system", f"redirect writes to {path}, a system path outside the repo"
    argv = command.argv
    if argv and argv[0] in {"cd", "pushd"}:
        target = argv[1] if len(argv) > 1 else "~"
        if target != "-":
            scope.cwd = scope.path(target)
        return None
    return _judge_program(argv, scope, depth)


def _judge_text(text: str, scope: Scope, depth: int = 0) -> Finding | None:
    if depth > MAX_NESTING:
        return None
    try:
        commands = simple_commands(tokenize(text))
    except ValueError:
        return None
    for command in commands:
        finding = _judge_command(command, scope, depth)
        if finding:
            return finding
    return None


def judge(command: str, cwd: Path, workspace: Path) -> Finding | None:
    """The first denied action in `command` run from `cwd`, or None when allowed."""
    root = git_root(workspace)
    scope = Scope(
        os.path.normpath(os.path.abspath(cwd)),
        os.path.expanduser("~"),
        str(root) if root else None,
    )
    return _judge_text(command, scope)


def handle(payload: dict[str, object], root: Path) -> tuple[int, dict[str, str]]:
    command = payload.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0, {"permission": "allow"}
    cwd = payload.get("cwd")
    finding = judge(command, Path(cwd) if isinstance(cwd, str) and cwd else root, root)
    if finding is None:
        return 0, {"permission": "allow"}
    key, reason = finding
    return DENY_EXIT, {
        "permission": "deny",
        "user_message": f"shell-guard blocked this command: {reason}.",
        "agent_message": f"shell-guard blocked `{command}`: {reason}. {GUIDANCE[key]}",
    }
