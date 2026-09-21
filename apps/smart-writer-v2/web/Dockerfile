# SUPERSEDED (D5 re-lock 2026-09-21) — do not ship.
#
# Product UI is the Next static export served by FastAPI on service
# `smart-writer-v2` (same-origin). See apps/smart-writer-v2/web/README.md
# and notes/packets/2026-09-21-swv2-d5-one-service-ui.md.
#
# This Dockerfile previously built a standalone Next server for a second
# Railway service `smart-writer-v2-ui`. That cattle path is retired.
# Prefer: cd web && npm run build:fastapi  → assets under app/static/ui
# then: nix build .#container-smart-writer-v2
