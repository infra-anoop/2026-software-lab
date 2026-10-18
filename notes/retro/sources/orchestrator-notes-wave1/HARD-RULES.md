# HARD RULES for the orchestrator (read before any git command)

1. NEVER put a heredoc (`cat >> ... <<EOF`), `echo >`, or any redirection in the SAME shell command as git.
   Such commands run SANDBOXED, and the sandbox IGNORES working_directory: they run in the PRIMARY checkout (main).
   Incidents: 10-07 ~11:18 PT (local commit on main, push refused) and 10-07 ~14:50 PT (2 cherry-picks + 2 commits on
   local main; pushes to main refused by the ruleset). Both cleaned with `git reset --hard <origin/main sha>` in the primary checkout.
2. Edit files with the editor tools (Read/StrReplace/Write). Run git in its own command, which matches the allowlist and runs unsandboxed in the worktree.
3. After any git chain, check `git log --oneline -1` output matches the expected worktree branch.
4. Governor asks go to bus/decisions/<id>/request.yaml (plain language; no ids or jargon like "worktree"), not chat questions.
5. Poll review branches in git after ~30 quiet minutes; completion notices get lost.
6. Never capture `nix develop` stdout into a variable; the banner pollutes it.
