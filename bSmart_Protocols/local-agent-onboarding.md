# bSmart Protocol: local agent onboarding

```yaml
protocol:
  id: local-agent-onboarding
  title: Local agent onboarding
  purpose: Provision named local host and Docker AI agents after the host tools and bSmart-System are available.
  use_when:
    - the operator explicitly asks to onboard local agents
    - Hermes/OpenCode and a model provider are already installed or configured
    - local Docker Desktop agents need isolated homes, workspaces, and launchers
  scope: local workstation only
  excludes:
    - VPS, Dokploy, EPS, or cloud deployment
    - bSmart instance-content onboarding
    - automatic publication or remote Git setup
  related_protocols:
    - bootstrap
    - instance-git-onboarding
    - project-storage
    - secret-provider-onboarding
```

## Boundary and starting assumptions

```yaml
starting_point:
  required_or_detected:
    - Hermes, OpenCode, or the selected host framework is installed
    - at least one model provider is already configured or available for later per-home authentication
    - bSmart-System is present in the current workspace or can be fetched from its public HTTPS remote
    - the workflow is initiated by the operator from the current host session
  default_agent_role: Admin
  local_only: true
```

This protocol is separate from bSmart's own `bSmart_Setup.md`. It provisions the local host/Docker structure and then hands each launched agent over to the operator for bSmart onboarding. It must not duplicate bSmart feature questions.

## Operator-controlled values

Ask only for values that materially change the installation. Inspect first and provide detected defaults.

```yaml
values:
  current_session:
    action: inspect current working directory, drive, host framework, and installed client versions
    rule: never silently treat an unrelated directory as the final agent workspace
  agent_root:
    default: derive from the current working location and drive; offer a sensible sibling such as `<current-drive>:\Agents`
    prompt: confirm or change the proposed agent root once
  agents:
    defaults:
      - Admin
      - Digtech
    prompt: confirm or change both display names
    validation:
      - unique
      - path-safe
      - safe for profile, Docker identity, shortcut, and Git branch identifiers
  optional_clients:
    choices:
      - Codex
      - OpenCode client/CLI
      - Claude client/CLI
    default: do not install unless selected
  instance_git: defer until the final section; ask independently for each agent
```

After confirmation, derive variables and reuse them throughout the workflow:

```text
AGENT_ROOT
ADMIN_NAME / ADMIN_WORKSPACE
DIGTECH_NAME / DIGTECH_WORKSPACE
```

Do not repeat hardcoded `Admin`, `Digtech`, or a drive letter after this point.

## Fixed workspace layout

For each agent workspace, create or verify this layout without asking the operator to customize individual folder names:

```text
<AGENT_WORKSPACE>\bSmart-System
<AGENT_WORKSPACE>\bSmart
<AGENT_WORKSPACE>\projects
<AGENT_WORKSPACE>\sandboxes
```

Optional extensions use:

```text
<AGENT_WORKSPACE>\bSmart-Extensions
```

`bSmart` and `sandboxes` are siblings. Never create the canonical sandbox inside `bSmart`. If a nested or duplicate sandbox is detected, stop, report the paths, and offer an approval-gated migration; do not silently create a second active root.

## Safe execution order

### 1. Preflight

Inspect and record, without changing anything:

- current working directory and drive;
- host framework and installed versions;
- available Codex, OpenCode, and Claude clients;
- Docker Desktop version, context, and running status;
- existing Hermes homes, profiles, desktop data directories, containers, and shortcuts;
- existing workspace hooks and bSmart files;
- current Git status where a repository already exists.

Back up relevant shortcuts, Hermes configuration, and local state before replacement. Never print credentials, OAuth stores, tokens, private keys, or `.env` contents.

### 2. Confirm paths and names

Confirm the proposed `AGENT_ROOT`, then confirm or change the two default names. Validate collisions before creating files, profiles, containers, or shortcuts.

### 3. Verify optional clients

Install only the clients selected by the operator, using current official installation guidance for the host platform. For every selected client, verify all of the following:

- executable/client is available;
- supported launcher or CLI accepts a working directory;
- launch starts in the requested agent workspace;
- the client does not silently fall back to a global/default directory.

OpenCode Desktop must not be treated as suitable if it cannot open in a specified folder; use the OpenCode client/CLI when that is the supported option. Apply the same working-directory test to Codex and Claude rather than assuming desktop and CLI behavior are equivalent.

### 4. Pull bSmart-System

For each agent workspace, clone or update the public reusable `bSmart-System` checkout. Keep it separate from the local `bSmart` content root. Do not put agent identity, site-local account names, or secrets in the system checkout.

### 5. Create isolated Hermes/Docker agents

Create separate local Docker agents for the confirmed names. Each agent requires its own:

- persistent Hermes home;
- desktop user-data directory;
- profile/session state;
- Docker/shared-container identity;
- workspace, `projects`, and `sandboxes` mounts;
- credential/authentication scope.

Use the installed Hermes documentation and supported configuration commands. Do not hand-edit configuration when a supported command exists. Do not copy `auth.json`, OAuth stores, sessions, rotating credentials, or scheduled jobs between homes.

The Docker image may be a verified current Hermes base image. Do not bake a stale `bSmart-System` checkout into the image. A reusable custom image is optional and should be considered only after a working container has been verified.

Required container defaults:

```yaml
working_dir: /workspace
environment:
  TERMINAL_CWD: /workspace
  HERMES_WRITE_SAFE_ROOT: /opt/data:/workspace:/projects:/sandboxes
volumes:
  - <agent-workspace>:/workspace
  - <agent-hermes-home>:/opt/data
  - <agent-projects>:/projects
  - <agent-sandboxes>:/sandboxes
```

Use the actual supported runtime configuration for the installed Hermes release. Do not assume these examples can be pasted unchanged into every host setup.

Before any live container recreation, capture the existing configuration and obtain operator approval.

### 6. Create and test launchers

Create three shortcuts or launchers using the confirmed names:

- `<Super Admin name>` — host mode, outside Docker;
- `<Admin name>` — Docker agent;
- `<Digtech name>` — Docker agent.

Each launcher must set or select the correct:

- Hermes home;
- desktop user-data directory;
- working directory;
- Docker identity where applicable;
- shared Hermes installation root.

Clear inherited terminal-directory overrides that could redirect a client. Do not put secrets in shortcut targets or arguments. Back up an existing shortcut before replacing it.

Launch and verify one at a time. Close the test instance before launching the next unless concurrent operation is explicitly requested.

### 7. Hand off to bSmart onboarding

After each agent launches, instruct the operator to explicitly initiate bSmart onboarding in that agent. This protocol should not repeat the questions or feature setup in `bSmart_Setup.md`.

Provide an editable identity-prompt example appropriate to the selected name and role.

Admin example:

> You are my system administrator on this computer. You help me manage this computer, its services, and other agents. Protect my personal information, credentials, tokens, passwords, private keys, session data, and company information. Inspect before changing anything, explain risky actions before performing them, prefer reversible changes and backups, and ask for my approval before destructive operations, broad permission changes, external publication, or changes to running services. Communicate concisely and clearly. Do not expose secrets in chat, files, logs, commits, or reports.

Digtech example:

> You are my personal work assistant and an expert in geophysics, geology, petrophysics, seismic interpretation, and burial history. Help me analyze, organize, research, and develop technical work while clearly distinguishing facts, interpretations, assumptions, and uncertainty. Protect my personal information, credentials, tokens, private keys, and company information as confidential. Do not expose or publish confidential data without my explicit approval. Inspect before changing files, preserve source material, prefer reversible changes, and ask before destructive or externally visible actions. Communicate concisely and clearly.

The operator may provide their own identity, role, goals, and communication preferences immediately or later. The operator may postpone bSmart Dreaming, extensions, project storage choices, and instance Git to the separate bSmart onboarding flow.

### 8. Final optional instance Git setup

Only after local infrastructure, isolation, launchers, bSmart handoff, authentication, and live inference are working, ask independently whether each agent should use Git for its private `bSmart` content.

If accepted, hand off to `instance-git-onboarding.md` and guide the operator one step at a time. A common GitHub pattern may be offered as an example, but public bSmart-System must remain provider/account/path-neutral:

- operator's GitHub account owns or creates the private instance repository;
- an AI or machine user may be invited as a collaborator;
- each independent instance uses a dedicated SSH key or other narrow authentication;
- repository access is verified before any push;
- secrets stay outside bSmart content, repositories, logs, and chat;
- branches and pull requests are preferred over direct default-branch pushes.

## Verification and completion

Do not report completion until applicable checks pass separately for each agent:

```yaml
acceptance:
  host:
    - Super Admin launches outside Docker
    - host working directory is correct
    - host launcher uses the intended name
  docker:
    - one intended container per Docker agent
    - Hermes homes and desktop data directories are isolated
    - container identities are distinct
    - /workspace maps to the intended agent workspace
    - /projects maps to the intended projects folder
    - /sandboxes maps to the intended sibling sandboxes folder
    - no unapproved broad host mounts exist
  clients:
    - selected clients launch in the intended working directory
  bsmart:
    - bSmart-System exists in each workspace
    - operator has explicitly initiated bSmart onboarding in each launched agent
  runtime:
    - harmless live inference succeeds for each agent, or is explicitly recorded as deferred
  git:
    - each agent's Git choice is recorded as enabled, declined, or deferred
```

If any item is unverified or deferred, state that plainly. Preserve backups and rollback information; never delete old homes, containers, shortcuts, images, or repositories as part of normal onboarding.

## Invocation

This process is operator-triggered, not part of every bSmart session startup. A supported host agent may invoke it when the operator asks for local-agent onboarding, for example:

```text
Start the bSmart local-agent onboarding process.
```

The invoking agent should load this protocol, inspect the current session, and proceed interactively with the approval gates above.
