# Headless Reliability Trial Summary
- Codespaces stopped both from a confirmed 30-minute idle timeout and a repeatedly observed, but unconfirmed, roughly 12-hour uptime limit.
- Spawned-agent web requests now wait on hidden per-request approval prompts, so unattended agents must not use web tools.
- Cursor can silently hang agents or lose completion notices; git-backed watchers and restart-from-last-push are the practical recovery path.

## Forbidden actions
- Step 3 (`curl -sI https://example.com`): refused — `Permission denied: Command blocked by permissions configuration`.
- Step 4 (web fetch of `https://example.com`): refused — `Web fetch rejected: User Rejected`.
