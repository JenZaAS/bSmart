# bSmart Protocol: instance Git onboarding

```yaml
protocol:
  id: instance-git-onboarding
  title: Instance Git onboarding
  purpose: Configure optional Git tracking and remote sync for one bSmart instance content root without mixing it with the reusable bSmart-System repo.
  use_when:
    - setting up or re-setting a bSmart instance
    - deciding whether /workspace/bSmart or ./bSmart should use Git
    - attaching a bSmart instance to an existing or new remote repo
    - configuring Git credentials for one AI instance
  content_root_container: /workspace/bSmart
  content_root_local: ./bSmart
  related_protocols:
    - secret-provider-onboarding
    - github-ai-access
    - project-storage
  nested_git_helper: /workspace/bSmart-System/scripts/bsmart-ignore-nested-git
```

## Core split

```yaml
repo_boundary:
  system_repo:
    purpose: reusable public bSmart framework and protocols
    usual_path_container: /workspace/bSmart-System
    usual_path_local: ./bSmart-System
    required_for_bsmart_updates: true
  instance_repo:
    purpose: local AI instance content, state, docs, workdocs, handoffs, and project metadata
    usual_path_container: /workspace/bSmart
    usual_path_local: ./bSmart
    optional: true
  rule:
    - do not confuse bSmart-System Git with instance/content Git
    - public bSmart-System must remain third-party reusable
    - instance Git may use local defaults, private repos, private auth, and site-local naming
    - system updates must never overwrite instance content
```

## Public system neutrality

```yaml
genericity_rules:
  bSmart_System_must_not_hardcode:
    - a specific GitHub/GitLab user
    - a specific organization or repo owner
    - one operator's repo naming convention
    - site-local host paths
    - private SSH key names as mandatory names
    - token names as mandatory names
    - secret values or unredacted credential responses
  bSmart_System_may_provide:
    - generic prompts
    - provider categories
    - schema examples with placeholder names
    - safe command templates
    - optional references for common providers such as GitHub
  instance_defaults_may_provide:
    - preferred provider
    - repo owner/account
    - repo naming pattern
    - actor identity
    - auth method
    - local secret provider profile
```

## Onboarding prompt flow

```yaml
prompt_flow:
  trigger:
    - during setup when instance_git has not been configured
    - operator explicitly asks to configure or streamline instance Git
  load_defaults_first:
    paths:
      - /workspace/bSmart/State/instance-git-defaults.yaml
      - ./bSmart/State/instance-git-defaults.yaml
    behavior:
      - treat defaults as suggestions only
      - explain that they are instance-local, not bSmart-System requirements
      - ask whether to use, edit, or ignore them
  question_1: |
    bSmart - Instance Git

    Should this AI instance use Git for its bSmart content root?
  choices_1:
    - No Git
    - Local Git only
    - Existing remote repo
    - Create/request new remote repo
```

## Mode behavior

```yaml
modes:
  none:
    meaning: no Git repo for the instance content root
    use_when:
      - temporary agent
      - disposable test instance
      - operator wants manual backups only
    actions:
      - record mode in local setup state if desired
      - do not run git init
      - do not ask for credentials
  local_git_only:
    meaning: local Git history without remote push/pull
    actions:
      - run git init in the content root after approval
      - create/update .gitignore with bSmart defaults
      - commit initial local snapshot if operator approves
    credentials: none
  existing_remote:
    meaning: attach content root to an operator-provided remote URL
    asks:
      - remote_url
      - default_branch
      - auth_method
    actions:
      - verify remote reachability without printing credentials
      - initialize or connect the local repo
      - fetch before pushing when remote is non-empty
      - avoid overwriting remote history without explicit approval
  create_new_remote:
    meaning: create or ask the operator/admin to create a new remote repo
    asks:
      - provider
      - owner_or_namespace
      - repo_name
      - visibility
      - who_will_create_remote: operator | authorized_agent | external_admin
      - auth_method
    actions:
      - draft creation command or UI steps
      - create only when the active agent has explicit permission and credentials
      - protect main/default branch where practical
```

## Auth choices

```yaml
auth_methods:
  none_pull_only:
    meaning: no push/API auth configured; operator handles remote writes manually
  existing_ssh_agent:
    meaning: use SSH agent/socket already available in the runtime
  mounted_ssh_key:
    meaning: use a read-only mounted key file and pinned known_hosts file
    required_metadata:
      - ssh_key_path
      - known_hosts_path
  deploy_key:
    meaning: repo-scoped SSH key, optionally write-enabled
    recommended_for: one private instance repo with narrow access
  token_file:
    meaning: token read from a mounted/read-only file for provider API commands
    notes:
      - use per command where possible
      - do not export globally unless operator accepts wider exposure
  secret_provider:
    meaning: retrieve required credential material through the configured secret-provider protocol, such as local mounts, deployer secrets, or an external vault/provider allowed by the operator
    dependency: secret-provider-onboarding
  manual:
    meaning: operator performs credential steps outside the agent and reports only verification result
```

```yaml
secret_provider_handoff:
  when:
    - auth_method == secret_provider
    - auth_method requires credentials and no local secret provider is configured
  check_paths:
    - /workspace/bSmart/State/secret-provider.yaml
    - ./bSmart/State/secret-provider.yaml
  if_missing:
    prompt: This Git setup needs credentials, but no secret provider is configured. Set one up now?
    choices:
      - Set up secret provider
      - Use mounted/manual credentials for this Git setup
      - Continue without push/API access
  required_logical_secrets:
    git_ssh_private_key:
      required_for:
        - ssh_clone
        - git_pull_private
        - git_push
    git_known_hosts:
      required_for:
        - ssh_host_key_pinning
    git_api_token:
      required_for:
        - create_remote_repo
        - open_pr
        - comment_on_pr_or_issue
      optional: true
```

## Instance-local defaults

```yaml
instance_git_defaults_spec:
  path: /workspace/bSmart/State/instance-git-defaults.yaml
  owner: instance_content_or_admin_tooling
  git_policy: may_be_committed_only_if_it_contains_no_secret_values
  example:
    instance_git_defaults:
      provider: github
      owner_or_namespace: ExampleOrg
      actor: example-machine-user-or-deploy-key
      repo_pattern: bSmart_<AgentName>
      default_branch: main
      preferred_mode: existing_remote
      auth_method: secret_provider
      secret_provider_profile: example-git
      direct_default_branch_push: false
      prefer_branches_and_prs: true
```

## Runtime spec written by onboarding

```yaml
instance_git_spec:
  path: /workspace/bSmart/State/instance-git.yaml
  owner: instance_content
  git_policy: may_be_committed_only_if_it_contains_no_secret_values_and_no_sensitive_provider_details
  example:
    instance_git:
      mode: existing_remote
      content_root: /workspace/bSmart
      remote_url: git@example.com:Owner/bSmart_Agent.git
      default_branch: main
      auth:
        method: secret_provider
        provider_ref: default
        required_secret_names:
          - git_ssh_private_key
          - git_known_hosts
          - git_api_token_optional
      policy:
        direct_default_branch_push: false
        prefer_branches_and_prs: true
        ignore_nested_git: true
```

## Git hygiene

```yaml
gitignore_policy:
  always_ignore:
    - secrets/
    - .secrets/
    - '*.pem'
    - '*.key'
    - '*.token'
    - .env
    - .env.*
    - .dreaming-backups/
  normally_ignore:
    - Sandboxes/
    - Mail/
    - runtime caches and generated artifacts
  nested_git:
    rule: external code repos inside projects are independent repos by default, not submodules
    before_commit: run bsmart-ignore-nested-git --check when helper exists
    fix_command: python3 /workspace/bSmart-System/scripts/bsmart-ignore-nested-git --fix --path /workspace/bSmart
    submodules: opt-in only after operator approval
```

## Safe verification

```yaml
verification:
  local_repo:
    - git -C <content-root> status --short
    - git -C <content-root> remote -v
  remote_ssh:
    - git ls-remote <remote-url> HEAD
  mounted_secrets:
    - ls -l /run/secrets
    - ssh-keygen -lf <public-key-path>
  provider_api:
    - use provider CLI/API identity command that prints account identity only, not tokens
  never:
    - print private keys
    - print tokens
    - commit secrets
    - force-push or reset remote history without explicit approval
```

## Provider-specific notes

```yaml
github_note:
  generic: For GitHub, SSH handles git transport; gh/API token is only needed for repo creation, PRs, issue/PR comments, or metadata operations.
  local_site_defaults: A specific deployment may recommend its own machine user, organization, deploy-key policy, and token storage, but those recommendations belong in instance-local content, not public bSmart-System.
```
