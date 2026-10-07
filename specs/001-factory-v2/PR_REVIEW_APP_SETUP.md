# PR review — GitHub App setup

## Decision

**Reject.** The permission scope, secret handling, decision request, and approving-review consequence match the factory locks, but two sets of literal GitHub UI instructions use stale or inexact labels.

## Findings

| id | severity | tag | location | issue | fix |
|----|----------|-----|----------|-------|-----|
| R-AS1 | Blocker | process | `notes/ops/2026-10-07-github-app-setup.md`, step 7 permission table | The three writable permission values say **Read and write**, but GitHub's current dropdown label is **Read & write**. The governor is instructed to follow labels literally, so the look-alike wording fails the required UI-label fidelity even though the intended permission level is correct. | Change the values for **Checks**, **Contents**, and **Pull requests** to **Read & write**. GitHub documents the exact dropdown values as **Read-only**, **Read & write**, and **No access**: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app |
| R-AS2 | Blocker | process | `notes/ops/2026-10-07-github-app-setup.md`, steps 10–11 | The credential instructions use the stale locations **About** and **Private keys** and the stale button **Generate a private key**. GitHub's current dedicated private-key instructions route through **Credentials** → **Key pairs** → **New key**. The current App ID instruction says to find the value next to **App ID** on the app settings page, not under **About**. | Replace step 10 with “On the app settings page, next to **App ID**, note the number.” Replace step 11 with “In the left sidebar, click **Credentials**, then **Key pairs**, then **New key**.” See https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps and https://docs.github.com/en/apps/creating-github-apps/writing-code-for-a-github-app/quickstart |

## Verified without findings

- The personal-account path, app-name and homepage fields, **Active**, installation visibility, creation, installation, repository selection, and Codespaces-secret labels match the current GitHub documentation.
- The App token needs **Contents**, **Pull requests**, and **Checks** at the locked levels. The factory uses it for authenticated Git fetch/push, pull-request reads and creation, review and check reads; status posting stays on the CI client. No Issues, Workflows, or Administration permission is needed by the reviewed agent commands.
- The secret names match `deploy/secrets/schema.yaml`; the full PEM is read as one environment value by typed settings and is never placed in git or chat.
- The decision request validates, uses plain language, recommends an exact option label, and fairly explains that automated Infisical access still needs a codespace-delivered credential.
- GitHub documents that a newly added Codespaces secret reaches an existing codespace after it is stopped and restarted: https://docs.github.com/en/codespaces/managing-your-codespaces/managing-your-account-specific-secrets-for-github-codespaces
- Requiring one approving review plus code-owner review matches the T065 amendment.

## Orchestrator triage (round 1)

| id | disposition | change |
|----|-------------|--------|
| R-AS1 | Accepted; confirmed against the registering-a-github-app page | Step 7 table: **Read & write** for Checks, Contents and Pull requests |
| R-AS2 | Accepted; confirmed against the managing-private-keys page | Step 10: the number next to **App ID**; step 11: **Credentials** → **Key pairs** → **New key** |
