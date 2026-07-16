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
  prompt_style: use button choices where supported
  prompt_text: |
    bSmart - Project configuration

    Choose location for project folders:

    1) Mounted volume
    Host/exchange folder mounted into the container.

    2) Internal bSmart
    bSmart’s standard project folder inside the container workspace.
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
  feedback_template: |
    bSmart - Project storage configured.

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
compose_boundary:
  bsmart_role: record desired storage and produce volume-line guidance
  user_role: apply Compose/Dokploy changes and redeploy
  sschwadmin_role: reconcile storage spec, image-source blueprint compose, and live Dokploy compose when readable
  dokploy_visibility_goal: provide SschwAdmin a narrow read-only helper for live Dokploy compose inspection
```
