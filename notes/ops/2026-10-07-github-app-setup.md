# Setting up the factory's GitHub App (governor steps)

Prepared by the orchestrator on 2026-10-07, after PR #33 merged the code that uses the App (task T065).

**What this is for.** Today every factory action on GitHub runs as you. With the App, the agents' commands (claims, handoffs, opening PRs, verdicts) run as the factory's own bot account, so git shows which actions were the factory's. The CI gate checks keep using the CI token. The App gets **no** permission to post commit statuses, so it cannot mark a check green (decision D8 of 2026-10-05).

**Time:** about 15 minutes, plus a codespace restart at a moment you choose.

**Before you start:** the open decision `bus/decisions/app-key-delivery/request.yaml` asks how the two values reach the codespace. Steps 1 to 13 are the same either way. Step 14 is option A, the recommended one.

## Part 1: create the App (github.com, in a browser)

1. Click your profile picture (top right), then **Settings**.
2. In the left sidebar, at the very bottom, click **Developer settings**.
3. Click **GitHub Apps**, then **New GitHub App**.
4. **GitHub App name:** `infra-anoop-factory`. Names are unique across GitHub; if it is taken, use `infra-anoop-factory-lab`. Tell the orchestrator which name you used.
5. **Homepage URL:** `https://github.com/infra-anoop/2026-software-lab`
6. **Webhook:** untick **Active**. No webhook URL is needed.
7. **Permissions**, then open **Repository permissions** and set exactly these:

   | Permission | Set to |
   |---|---|
   | **Checks** | Read and write |
   | **Contents** | Read and write |
   | **Metadata** | Read-only (GitHub sets this itself) |
   | **Pull requests** | Read and write |
   | **Commit statuses** | **No access** (leave it) |
   | **Workflows** | **No access** (leave it) |
   | everything else | No access |

   Look-alike: **Checks** and **Commit statuses** are different entries. Only **Checks** gets write.
   Leave **Organization permissions** and **Account permissions** all at No access.

   With **Workflows** at No access, the App cannot push changes to files under `.github/workflows/`. Those files are already yours to approve (they are rule paths), and a factory change to them will need a push by you.
8. **Where can this GitHub App be installed?:** choose **Only on this account**.
9. Click **Create GitHub App**.
10. On the page that opens, near the top under **About**, note the **App ID** (a number).
11. Scroll down to **Private keys** and click **Generate a private key**. A file ending in `.pem` downloads. Keep it out of the repo and out of the chat.

## Part 2: install it on this repo

12. In the App's left sidebar, click **Install App**, then **Install** next to `infra-anoop`.
    - Choose **Only select repositories**, pick `2026-software-lab`, then click **Install**.

## Part 3: store the two values in Infisical (the source of truth)

13. In Infisical, open project `2026-software-lab`, environment `production`, path `/`, and add two secrets:
    - `FACTORY_GITHUB_APP_ID`: the App ID from step 10.
    - `FACTORY_GITHUB_APP_PRIVATE_KEY`: the whole text of the `.pem` file, including the `-----BEGIN` and `-----END` lines.

## Part 4 (option A): give the codespace the same two values

14. On github.com, click your profile picture, then **Settings**. In the left sidebar, under **Code, planning, and automation**, click **Codespaces**.
    - Under **Codespaces secrets**, click **New secret**.
    - **Name:** `FACTORY_GITHUB_APP_ID`, **Value:** the App ID. Under **Repository access**, pick `infra-anoop/2026-software-lab`, then click **Add secret**.
    - Repeat for `FACTORY_GITHUB_APP_PRIVATE_KEY`, with the whole `.pem` text as the value.
15. The codespace sees new secrets only after a restart. Restart it when it suits you; the end of the day is fine, since the codespace stops around then anyway. Work in progress is pushed to git, and the orchestrator picks up from there.
16. Once both stores hold the key, delete the downloaded `.pem` file from your computer.

## What happens next (orchestrator, after the restart)

- **Read-back:** mint one installation token from the codespace and check the permissions GitHub reports for it: contents, pull requests and checks writable, commit statuses absent. Nothing is changed before that check passes.
- **Switch the factory over:** a PR flips the factory to verified mode. The same PR records that `main` requires code-owner review and at least one approving review.
- **Then one more click for you,** in the `main` ruleset: turn on the required approving review and code-owner review. The orchestrator will give exact steps when the PR is ready.

**What changes for you after that click:** every PR then needs one approving review before it can merge. The factory's own account opens the PRs, so you can approve them, but merges that today happen on green checks alone will wait for your approval.
