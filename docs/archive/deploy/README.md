# Archived deploy artifacts

Historical backups and design notes kept for reference. **Not used by CI.**

| File | Description |
|---|---|
| `deploy.-backup_2.yml` | Earlier reusable Railway deploy workflow |
| `deploy_api_backup.uml` | Full GraphQL deploy workflow (pre-streamline) |
| `DEPLOY_COMPARISON.md` | Why deploy uses GraphQL vs pure Railway CLI |
| `production_old.yml` | Pre–per-app Railway layout (single-file config) |

Active workflows and config live under:

- `.github/workflows/deploy.yml`
- `.github/workflows/ci-cd-pipeline.yml`
- `deploy/railway/<environment>/<app_id>.yml`
