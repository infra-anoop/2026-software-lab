"""POSIX-shell-style tokenizer for `shell-guard`: what would the shell execute?

Honors single and double quotes, backslash escapes and line continuations, `#` comments
at a word start, and the control/redirection operators. Text that is quoted or
commented is never a command. Not a full shell: expansions are left as literal text.
"""

from __future__ import annotations

OPERATOR_CHARS = frozenset(";&|()<>")
OPERATORS = sorted(
    [";;", "&&", "||", "|&", ">>", ">&", "&>>", "&>", ">|", "<<<", "<<", "<&", "<>"]
    + [";", "&", "|", "(", ")", "<", ">"],
    key=len,
    reverse=True,
)
DOUBLE_QUOTE_ESCAPES = frozenset('"\\$`\n')


class Token:
    __slots__ = ("operator", "text")

    def __init__(self, text: str, operator: bool = False) -> None:
        self.text = text
        self.operator = operator

    @property
    def redirect(self) -> bool:
        return self.operator and ("<" in self.text or ">" in self.text)


class SimpleCommand:
    __slots__ = ("argv", "redirects")

    def __init__(self) -> None:
        self.argv: list[str] = []
        self.redirects: list[tuple[str, str]] = []


def tokenize(text: str) -> list[Token]:
    """Words and operators; raises ValueError on an unterminated quote."""
    tokens: list[Token] = []
    word: list[str] = []
    in_word = False
    i, n = 0, len(text)

    def flush() -> None:
        nonlocal in_word
        if in_word:
            tokens.append(Token("".join(word)))
        word.clear()
        in_word = False

    while i < n:
        char = text[i]
        if char in " \t\r":
            flush()
            i += 1
        elif char == "\n":
            flush()
            tokens.append(Token("\n", operator=True))
            i += 1
        elif char == "#" and not in_word:
            end = text.find("\n", i)
            i = n if end < 0 else end
        elif char == "\\":
            if i + 1 < n and text[i + 1] != "\n":
                word.append(text[i + 1])
                in_word = True
            i += 2
        elif char == "'" or (char == "$" and text.startswith("'", i + 1)):
            start = i + (2 if char == "$" else 1)
            end = text.find("'", start)
            if end < 0:
                raise ValueError("unterminated single quote")
            word.append(text[start:end])
            in_word = True
            i = end + 1
        elif char == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n and text[i + 1] in DOUBLE_QUOTE_ESCAPES:
                    if text[i + 1] != "\n":
                        word.append(text[i + 1])
                    i += 2
                    continue
                word.append(text[i])
                i += 1
            if i >= n:
                raise ValueError("unterminated double quote")
            in_word = True
            i += 1
        elif char in OPERATOR_CHARS:
            if char in "<>" and in_word and "".join(word).isdigit():
                word.clear()  # file-descriptor prefix such as `2>`
                in_word = False
            flush()
            operator = next(op for op in OPERATORS if text.startswith(op, i))
            tokens.append(Token(operator, operator=True))
            i += len(operator)
        else:
            word.append(char)
            in_word = True
            i += 1
    flush()
    return tokens


def simple_commands(tokens: list[Token]) -> list[SimpleCommand]:
    """Split tokens at control operators; redirections keep their target word."""
    commands: list[SimpleCommand] = []
    current = SimpleCommand()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.redirect:
            target = tokens[i + 1] if i + 1 < len(tokens) else None
            if target is not None and not target.operator:
                current.redirects.append((token.text, target.text))
                i += 1
        elif token.operator:
            if current.argv or current.redirects:
                commands.append(current)
            current = SimpleCommand()
        else:
            current.argv.append(token.text)
        i += 1
    if current.argv or current.redirects:
        commands.append(current)
    return commands
