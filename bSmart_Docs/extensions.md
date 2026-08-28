# bSmart extensions

```yaml
extensions_root: /workspace/bSmart-Extensions
bundled_source_root: /workspace/bSmart-System/bSmart-Extensions
model: sibling_folder_per_extension
packaging_types:
  - bundled_with_bsmart
  - external_optional
```

## bSearch

```yaml
name: bSearch
path: /workspace/bSmart-Extensions/bSearch
source_path: /workspace/bSmart-System/bSmart-Extensions/bSearch
license: MIT
status: optional_bundled_extension
purpose:
  - scheduled AI-driven knowledge search
  - curated shortlist delivery
  - editable user-interest profile
  - feedback learning and searchable knowledge repository
install_model: copy_or_sync_from_bundled_source
setup_default: yes
```

Setup should ask whether to install/enable bSearch and show a short explanation of what it does.

## Fabric

```yaml
name: Fabric
path: /workspace/bSmart-Extensions/Fabric
source: https://github.com/danielmiessler/Fabric
license: MIT
status: optional
purpose:
  - prompt patterns
  - thinking strategies
  - reusable analysis workflows
```

Setup should ask whether to install/enable Fabric, default yes.

## Graphify

```yaml
name: Graphify
path: /workspace/bSmart-Extensions/Graphify
source_path: /workspace/bSmart-System/bSmart-Extensions/Graphify
license: MIT
status: optional_bundled_extension
purpose:
  - controlled baseline-vs-Graphify evaluation kit
  - reusable worker prompts and Hermes metrics collection
  - future bGraph/backend comparison tests on code-heavy corpora
install_model: copy_or_sync_from_bundled_source
setup_default: no
```

Setup may ask whether to install/enable the Graphify evaluation kit when the AI container will run codebase/tool-comparison experiments.

## bWorkflow

```yaml
name: bWorkflow
path: /workspace/bSmart-Extensions/bWorkflow
source_path: /workspace/bSmart-System/bSmart-Extensions/bWorkflow
status: optional_bundled_extension
purpose:
  - reusable workflow/procedure memory
  - Markdown-authoritative workflow catalogues
  - compact workflow trust/evidence counters
install_model: copy_or_sync_from_bundled_source
setup_default: yes
```

bWorkflow stores learned workflow content under `/workspace/bSmart/Workflows`, not in the packaged system tree by default.

## bSelective

```yaml
name: bSelective
path: /workspace/bSmart-Extensions/bSelective
source_path: /workspace/bSmart-System/bSmart-Extensions/bSelective
status: optional_bundled_extension
purpose:
  - deterministic selective source-context retrieval
  - initial MATLAB `.m` adapter
  - whole-file fallback when selective slices are insufficient
install_model: copy_or_sync_from_bundled_source
setup_default: yes
```

bSelective is off by default in a session; agents enable it by reading the adapter prompt/protocol when relevant.

## bSwarm

```yaml
name: bSwarm
path: /workspace/bSmart-Extensions/bSwarm
source_path: /workspace/bSmart-System/bSmart-Extensions/bSwarm
status: optional_bundled_extension
purpose:
  - chat-driven multi-agent orchestration protocol
  - unsupervised and supervised swarm modes
  - A/B report and self-improving comparisons
  - run statistics and bSelective integration
  - `critcascade`: depth-3 stepwise cascade with architect/programmer critics and bounded score-based repair loops
install_model: copy_or_sync_from_bundled_source
setup_default: yes
```

bSwarm v1 is a chat protocol, not a command handler. It uses concise run specs, grouped editing, Hermes delegation where useful, and Markdown run records.
