# System vs content

```yaml
system:
  root: /workspace/bSmart-System
  git_repo: true
  safe_to_pull: true
  owns:
    - bootstrap manifest
    - setup procedure
    - protocols
    - templates
    - docs
    - examples
    - version/changelog

content:
  root: /workspace/bSmart
  git_repo: optional_separate_repo
  safe_to_overwrite_by_system: false
  owns:
    - local agent identity
    - local state
    - TODO
    - log
    - projects
    - workdocs
    - library
```

```yaml
rule: all system in bSmart-System, all content in bSmart
```
