# Deployment Configuration

This directory contains deployment configurations for all environments.

## Structure
```
deploy/
├── railway/              # Railway deployment configs
│   ├── production.yaml   # Production environment
│   └── staging.yaml      # Staging environment
└── README.md            # This file
```

## How Deployment Works

1. **Build**: Nix builds container image (see `/flake.nix`)
2. **Push**: GitHub Actions pushes to GHCR
3. **Deploy**: GitHub Actions uses configs in this directory to deploy to Railway

## Deploying

### Production
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Staging (Manual)
```bash
gh workflow run deploy.yml -f environment=staging
```

## Modifying Deployment Config

1. Edit the appropriate YAML file
2. Commit and push
3. Next deployment will use new config

## Service Names

- **Production**: `research-auditor`
- **Staging**: `research-auditor-staging`

These are queried by name (not hardcoded IDs).