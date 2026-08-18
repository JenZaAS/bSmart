# bSmart Protocol: secret-provider onboarding

```yaml
protocol:
  id: secret-provider-onboarding
  title: Secret-provider onboarding
  purpose: Configure how one bSmart instance retrieves credentials without storing secret values in bSmart-System, bSmart content, project folders, logs, or chat.
  use_when:
    - setting up a new bSmart instance that needs credentials
    - configuring Git/auth, API providers, mail, webhooks, model providers, or deployment integrations
    - another onboarding flow needs a secret provider and none is configured yet
  output_spec: /workspace/bSmart/State/secret-provider.yaml
  local_default_spec: /workspace/bSmart/State/secret-provider-defaults.yaml
```

## Boundary

```yaml
system_boundary:
  bSmart_System_may_define:
    - provider types
    - required metadata fields
    - prompts and validation rules
    - logical secret-name conventions
    - safe verification patterns that do not print secret values
  bSmart_System_must_not_define:
    - real secret values
    - site-local API keys or tokens
    - private SSH keys
    - one operator's mandatory GitHub account, organization, host path, or vault endpoint
    - provider-specific credentials for third-party users
  instance_content_may_define:
    - chosen provider mode
    - non-secret endpoint or profile names
    - logical secret aliases
    - local defaults suggested by the operator/admin instance
  never_store_secrets_in:
    - /workspace/bSmart-System
    - /workspace/bSmart
    - /projects
    - /sandboxes
    - bSmart logs, TODOs, workdocs, or chat transcripts
```

## Provider choices

```yaml
secret_provider_modes:
  none:
    meaning: This instance has no configured secret provider.
    use_when: temporary/local-only instance or no integrations need credentials.
  local_file_mount:
    meaning: Secrets are mounted as files, usually read-only, into the runtime.
    examples:
      - /run/secrets/<logical-name>
    notes:
      - preferred for Docker/Dokploy when a service-specific secret directory is mounted read-only
      - file paths are metadata; file contents are never copied into bSmart files
  environment_variable:
    meaning: Runtime exposes selected secrets as environment variables.
    notes:
      - convenient but broader exposure inside the process environment
      - do not write env var values to files, logs, or chat
  docker_or_dokploy_secret:
    meaning: The deployer manages secret objects and injects them into the container.
    notes:
      - prefer read-only file injection when available
      - record only logical names and mount paths
  external_vault:
    meaning: A third-party or self-hosted vault provides secrets.
    examples:
      - 1Password
      - Bitwarden
      - HashiCorp Vault
      - cloud secret manager
      - other operator-provided provider
  manual:
    meaning: The operator handles credentials outside bSmart and supplies one-off commands or mounts.
```

## Onboarding prompt flow

```yaml
prompt_flow:
  trigger:
    - /workspace/bSmart/State/secret-provider.yaml missing and a feature needs credentials
    - operator explicitly asks to configure secrets
  initial_question: |
    bSmart - Secret provider

    How should this AI instance retrieve secrets when a feature needs credentials?
  choices:
    - No secret provider
    - Mounted/local/deployer secrets
    - External vault
    - Manual / no provider
  if_instance_defaults_exist:
    path: /workspace/bSmart/State/secret-provider-defaults.yaml
    behavior:
      - read defaults first
      - show defaults as suggestions, not system requirements
      - ask whether to use, edit, or ignore the defaults
```

## Metadata specs

```yaml
secret_provider_spec:
  path: /workspace/bSmart/State/secret-provider.yaml
  owner: instance_content
  git_policy: may_be_committed_only_if_it_contains_no_secret_values_and_no_sensitive_endpoint_details
  example:
    secret_provider:
      mode: local_file_mount
      mount_root: /run/secrets
      required_secret_names:
        github_ssh_private_key:
          path: /run/secrets/git_ssh_key
          required_for:
            - git_push
        github_known_hosts:
          path: /run/secrets/git_known_hosts
          required_for:
            - git_ssh_transport
        github_token:
          path: /run/secrets/github_token
          required_for:
            - gh_api
          optional: true
```

## Verification rules

```yaml
verification:
  safe_checks:
    - confirm provider config file exists
    - confirm required secret names are declared
    - confirm mounted secret files exist and have restrictive permissions, without reading contents
    - confirm external vault/provider can answer a metadata/health request without returning secret values
    - confirm Git/API tools work through their normal no-secret-print commands
  forbidden_checks:
    - cat private keys or tokens
    - paste secret values into chat
    - commit secret values or unredacted provider responses
    - log raw provider payloads that may contain secrets
```

## Handoff to other onboarding flows

```yaml
handoff_contract:
  called_by:
    - instance-git-onboarding
    - mail provider setup
    - model/API provider setup
    - webhook setup
    - deployment integration setup
  if_missing:
    question: This setup needs credentials, but no secret provider is configured. Set one up now?
    choices:
      - Set up secret provider
      - Use manual credentials for this one setup
      - Continue without credentialed features
  returns:
    - provider mode
    - non-secret endpoint/profile metadata when safe
    - logical secret names or file paths
    - verification commands that do not print secrets
```
