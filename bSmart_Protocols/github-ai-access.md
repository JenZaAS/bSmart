# bSmart Protocol: GitHub access for AI containers

```yaml
protocol:
  id: github-ai-access
  title: GitHub access for AI containers
  purpose: Configure GitHub repository and API access for one bSmart-aware AI instance without placing credentials in images, repos, workspaces, logs, or chat.
  use_when:
    - instance-git-onboarding chooses GitHub as the provider
    - an AI container needs GitHub clone, pull, push, PR, issue, or comment access
    - troubleshooting GitHub SSH/token access for a bSmart instance
  related_protocols:
    - instance-git-onboarding
    - secret-provider-onboarding
```

## Public-system boundary

```yaml
genericity:
  rule: This protocol is reusable bSmart-System guidance and must not require one operator's GitHub account, organization, repo owner, host paths, SSH key names, token names, or secret-provider endpoint.
  instance_specific_values_belong_in:
    - /workspace/bSmart/State/instance-git-defaults.yaml
    - /workspace/bSmart/State/instance-git.yaml
    - /workspace/bSmart/State/secret-provider.yaml
    - /workspace/bSmart/Docs/github/
  examples_are_placeholders: true
  never_store:
    - private keys
    - tokens
    - unredacted secret-provider responses
    - personal access token scopes tied to an actual secret value
```

## Goals

```yaml
goals:
  - grant repository access case-by-case, not globally
  - keep credentials outside Docker images, Git repositories, /workspace, project folders, logs, and chat
  - support different GitHub users, organizations, deploy keys, and auth policies per instance
  - prefer branches and PRs for updates
  - avoid direct pushes to main/default branch unless the operator explicitly approves
```

## Identity and attribution

```yaml
github_identity:
  choices:
    - operator_personal_account
    - project_or_org_machine_user
    - repo_deploy_key
    - GitHub App
    - other operator-approved model
  selection_rule: The reusable system asks or reads instance-local defaults; it does not hardcode the account.
```

Public GitHub comments/posts must be shown to the operator in full before posting. Approval is for the exact text, not just the idea of posting.

Optional instance-local signature templates may live in `/workspace/bSmart/Docs/github/` or the instance Git defaults. Do not put one operator's mandatory public signature in this generic protocol.

## Credentials: SSH vs token

Use SSH and token/API auth for different jobs:

| Credential | Used for | Notes |
|---|---|---|
| SSH key or deploy key | `git clone`, `git pull`, `git push` | Preferred for private repo git transport. |
| GitHub token / `GH_TOKEN` / GitHub App token | `gh` API actions: repo creation, PR comments, issue comments, PR metadata, releases | SSH alone is not enough for GitHub API comments. |

```yaml
credential_rules:
  ssh:
    - use a dedicated key per trusted instance or a repo-scoped deploy key when narrow access is enough
    - pin GitHub host keys through known_hosts
    - avoid StrictHostKeyChecking=no
  token:
    - use the minimum permissions/repository selection needed
    - read from a secret provider or mounted file only for commands that need API access
    - do not export globally unless the operator accepts broader runtime exposure
  common_pitfall: A token may identify as the expected GitHub actor but still return 404 for private repos when repository selection or scopes are insufficient.
```

## Secret-provider integration

```yaml
secret_provider:
  preferred_flow: configure through /workspace/bSmart-System/bSmart_Protocols/secret-provider-onboarding.md when credentials are not already mounted or otherwise available
  supported_sources:
    - local_file_mount
    - docker_or_dokploy_secret
    - environment_variable
    - external_vault
    - manual
  logical_secret_names:
    github_ssh_private_key:
      required_for:
        - git_ssh_transport
    github_ssh_public_key:
      optional: true
      safe_to_show: true
    github_known_hosts:
      required_for:
        - git_ssh_transport
    github_token:
      required_for:
        - gh_api
      optional: true
```

## Container secrets pattern

For Docker/Dokploy-like containers, each AI container should have its own secret source mounted read-only, commonly as `/run/secrets`.

Generic expected files when using local file mounts:

```text
/run/secrets/<git-ssh-private-key>   # private SSH key; never print
/run/secrets/<git-ssh-public-key>    # public SSH key; safe to show
/run/secrets/<github-known-hosts>     # pinned GitHub host keys
/run/secrets/<github-token>           # optional token for gh/API; never print
```

Generic Compose pattern:

```yaml
volumes:
  - <host-or-deployer-secret-source>:/run/secrets:ro
environment:
  GIT_SSH_COMMAND: "ssh -i /run/secrets/<git-ssh-private-key> -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/run/secrets/<github-known-hosts>"
```

Recommended runtime split:

- Put `GIT_SSH_COMMAND` in the container environment when ordinary `git fetch`, `git pull`, and `git push` should automatically use the mounted key.
- Keep `GH_TOKEN` file-based or provider-supplied by default; pass it per command, e.g. `GH_TOKEN="$(cat /run/secrets/<github-token>)" gh ...`.
- Do not print tokens or private keys.

## GitHub-side repo access workflow

For a private repo:

1. Choose the GitHub actor for this instance: machine user, personal account, GitHub App, or deploy key.
2. Grant least privilege to the exact repository or repository set:
   - Read for inspection/pull-only work.
   - Write for branch pushes and PRs.
   - Admin only when truly required.
3. Protect `main`/default branch where practical:
   - require PR before merge,
   - avoid direct pushes by AI containers unless explicitly approved.
4. Add public SSH key or configure deploy key/App credentials if using SSH transport.
5. Configure token/App permissions only when API actions are needed.

## Container-side verification

Inside the target container, verify without printing secret values.

```bash
id
ls -l /run/secrets
ssh-keygen -lf /run/secrets/<git-ssh-public-key>
GIT_SSH_COMMAND="ssh -i /run/secrets/<git-ssh-private-key> -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/run/secrets/<github-known-hosts>" \
  git ls-remote git@github.com:<owner>/<repo>.git HEAD
```

If `gh` is needed and a token is available as a mounted file:

```bash
GH_TOKEN="$(cat /run/secrets/<github-token>)" gh auth status
GH_TOKEN="$(cat /run/secrets/<github-token>)" gh api user --jq '.login + " " + .html_url'
```

Expected actor should match the instance-local default or operator-selected account.

If plain `git` fails with `Permission denied (publickey)` but an explicit command using the mounted key works, the live runtime is probably missing `GIT_SSH_COMMAND` or running from stale Compose/Dokploy configuration. Update the authoritative deployment configuration, redeploy/recreate the container, then verify the environment inside the live container.

## Clone/update workflow

Clone private repos into the configured project or content root, depending on purpose:

```bash
git clone git@github.com:<owner>/<repo>.git <target-path>
```

For updates:

```bash
cd <target-path>
git status
git switch -c ai/<short-task-name>
# edit/test
git add <files>
git commit -m "<concise message>"
git push -u origin ai/<short-task-name>
```

Then create a PR with `gh` if token/API auth exists, or ask the operator to open the PR manually.

## Instance-local defaults example

This example belongs in an instance-local defaults file, not as a public-system requirement:

```yaml
instance_git_defaults:
  provider: github
  owner_or_namespace: ExampleOrg
  actor: example-machine-user
  repo_pattern: bSmart_<AgentName>
  auth_method: secret_provider
  secret_provider_profile: example-github
  prefer_branches_and_prs: true
  direct_default_branch_push: false
```

## Guardrails

```yaml
guardrails:
  - never print or paste private keys/tokens into chats, logs, docs, or commits
  - never bake credentials into images
  - never commit credentials to bSmart or project repositories
  - prefer least-privilege, per-instance or per-repo credentials
  - treat shared tokens as higher blast-radius and document rotation impact locally
  - public GitHub comments require full-text operator approval before posting
  - if the target PR was superseded/closed, check for the successor and ask before posting to the new target unless approval clearly covers it
```
