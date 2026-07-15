# bSmart bundled extensions

```yaml
purpose: Source-packaged optional extensions that ship with bSmart-System.
root: /workspace/bSmart-System/bSmart-Extensions
installed_root: /workspace/bSmart-Extensions
```

These folders are the packaged source for optional bSmart extensions that are distributed with the system repo.

Rules:
- Keep packaged extension source in this folder.
- Keep installed/enabled instance copies under `/workspace/bSmart-Extensions`.
- Setup may ask whether to install a bundled extension by copying or syncing it from this source root into the installed root.
- Bundled extensions are optional even though they ship with bSmart.
- External optional extensions such as Fabric may still live only in `/workspace/bSmart-Extensions` until vendoring policy is finalized.
