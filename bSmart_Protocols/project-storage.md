# bSmart Protocol: project storage

```yaml
protocol:
  id: project-storage
  title: Project storage
  purpose: Define canonical project and sandbox paths for a bSmart-enabled AI instance running in a container.
```

```yaml
project_root_selection:
  canonical_container_path: /projects
  fallback_container_path: /workspace/bSmart/Projects
  rule:
    - if /projects exists and is readable/writable: use /projects
    - else use /workspace/bSmart/Projects
    - else run project-storage setup
```

```yaml
project_storage_setup:
  trigger: /workspace/bSmart/State/container-storage.yaml missing
  daily_check_helper: /workspace/bSmart-System/scripts/bsmart-startup-check
  storage_helper: /workspace/bSmart-System/scripts/bsmart-project-storage-check
  daily_state_file: /workspace/bSmart/State/bsmart-startup-check.yaml
  prompt_style: use Telegram button choices through the clarify tool where supported; do not replace this with a plain-text question on Telegram
  prompt_text: |
    bSmart - Project configuration

    Choose location for project folders:

    1) Mounted volume (e.g. external to Docker image and possibly a mounted SMB drive)

    2) Internal bSmart (standard bSmart project folder inside the container workspace)

    Some things will be stored in an internal project sandbox.
  choices:
    - Mounted volume
    - Internal bSmart
```

```yaml
mounted_volume_flow:
  after_choice: Mounted volume
  followup_prompt: |
    bSmart - Mounted project volume selected.

    Enter host-project-folder, e.g.

    /mnt/share/MyAI
  save:
    mode: mounted
    project_root: /projects
    host_project_folder: operator_value
  predeploy_prepare:
    rule:
      - before telling the operator to add a Compose/Dokploy volume, make sure the host project folder exists
      - if the folder is reachable from the agent through an existing writable host/share mount, create it directly and verify readability/writability
      - if the folder is not reachable from the agent, give one explicit host command to create it before the volume-line instruction
      - for SMB/CIFS project folders, prefer relying on the mount uid/gid/file_mode/dir_mode options rather than chowning files on the share
    host_command_template: mkdir -p {host_project_folder}
  feedback_template: |
    bSmart - Project storage configured.

    First ensure the host folder exists:

    mkdir -p {host_project_folder}

    Add following volume to Docker Compose file:

    - {host_project_folder}:/projects:rw

    After redeploy, this AI instance will use /projects for project folders.
```

```yaml
internal_bsmart_flow:
  after_choice: Internal bSmart
  infer_host_workspace:
    preferred: findmnt -T /workspace -n -o SOURCE
    parse: extract bracketed source path, e.g. /dev/sda1[/opt/docker-workspace/<instance>/workspace]
    fallback: ask operator for host path backing /workspace
  save:
    mode: internal_bsmart
    project_root: /projects
    host_project_folder: <host_workspace>/bSmart/Projects
  feedback_template: |
    bSmart - Project storage configured.

    Add following volume to Docker Compose file:

    - {host_workspace}/bSmart/Projects:/projects:rw

    After redeploy, this AI instance will use /projects for project folders.
```

```yaml
sandbox_storage:
  canonical_container_path: /sandboxes
  structure: /sandboxes/<project-slug>
  git_policy: outside instance Git by default
  setup_visibility: do not explain sandbox details during project-storage setup unless operator asks
  compose_recommendation: /opt/docker-workspace/<instance>/sandboxes:/sandboxes:rw
  predeploy_prepare:
    rule: create and permission the host sandbox folder before suggesting/adding the /sandboxes volume
    host_command_template: mkdir -p /opt/docker-workspace/<instance>/sandboxes && chown 10000:10000 /opt/docker-workspace/<instance>/sandboxes && chmod 775 /opt/docker-workspace/<instance>/sandboxes
  fallback: legacy per-project sandbox under /workspace/bSmart/Projects/<project>/sandbox when /sandboxes is unavailable
```

```yaml
container_storage_spec:
  path: /workspace/bSmart/State/container-storage.yaml
  scope: one reality for the whole AI instance
  not_in_project_volume: true
  minimum_fields:
    project_storage:
      mode: mounted | internal_bsmart
      project_root: /projects
      host_project_folder: host path used in Compose
    sandbox_storage:
      sandbox_root: /sandboxes
      mode: vps_local_preferred
```

```yaml
startup_check_behavior:
  helper: /workspace/bSmart-System/scripts/bsmart-startup-check
  cadence: once per UTC day
  force_option: --force
  no_side_effects_by_default:
    - does not create container-storage.yaml
    - does not edit Docker Compose or Dokploy
    - does not deploy, restart, chmod, chown, or mount anything
  reports_setup_required_when:
    - /workspace/bSmart/State/container-storage.yaml is missing
  throttle_exception:
    - missing container-storage.yaml must still be reported even if the daily startup check already ran today
  local_spec_creation:
    mounted_volume: bsmart-project-storage-check --configure-mounted --host-project-folder <host-path>
    internal_bsmart: bsmart-project-storage-check --configure-internal
```

```yaml
compose_boundary:
  bsmart_role: record desired storage and produce volume-line guidance
  user_role: apply Compose/Dokploy changes and redeploy
  sschwadmin_role: reconcile storage spec, image-source blueprint compose, and live Dokploy compose when readable
  dokploy_visibility_goal: provide SschwAdmin a narrow read-only helper for live Dokploy compose inspection
```
