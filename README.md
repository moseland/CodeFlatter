# CodeFlatter

> 🚧  Active-hobby code—expect the occasional bug.  
> Found one? Open an issue or PR!

A tiny pair of zero-dependency Python scripts that

1. **flatten** a project folder into a single markdown report  
2. let an LLM (or you) **patch the project back** by pasting blocks into stdin

---

## Installation

No packages to install—just drop the two files anywhere in your `$PATH` (or side-by-side in the repo).

```bash
chmod +x flatten.py ai_patch.py
```

---

## `flatten.py`

Generate a self-contained `PROJECT_DUMP.md` file with

* a directory tree  
* collapsible `<details>` blocks that contain the full source of every file you *didn’t* exclude

### Quick start

```bash
python flatten.py --root ./my-project --out PROJECT_DUMP.md
```

### Ignoring stuff

| flag               | meaning                             | example |
|--------------------|-------------------------------------|---------|
| `--skip-name`      | exact basename                      | `README.md` |
| `--skip-ext`       | extension wildcard (case-insensitive) | `.min.js` |
| `--skip-dir`       | directory basename                  | `node_modules` |
| `--skip-path`      | relative path (glob-friendly)       | `dist/**` |

Combine as often as you like; `.gitignore` patterns are also honored.

Example that skips common build artefacts:

```bash
python flatten.py \
  --root ./my-project \
  --skip-path dist \
  --skip-path node_modules \
  --skip-path assets/images \
  --skip-dir vendor \
  --skip-ext .min.js --skip-ext .wasm --skip-ext .data
```

---

## `ai_patch.py`

Paste (or pipe) a block like the one below into the script; it applies the diff or full-file replacement and writes the changes to disk.

```text
## replace-start: src/main.js
// entire new contents here
## replace-end
```

or unified-diff style

```text
## patch-start: src/utils.py
--- src/utils.py
+++ src/utils.py
@@ -5,7 +5,9 @@
- old line
+ new line
## patch-end
```

or delete a file

```text
## delete: tmp/leftovers.json
```

Usage:

```bash
cat patches.txt | python ai_patch.py [--dry-run]
```

`--dry-run` only prints what *would* change.

---

## Tips for LLM prompting

After you send `PROJECT_DUMP.md`, you can ask the model:

> “Return only the blocks `## replace-start`, `## patch-start`, or `## delete:` that are needed to apply the requested changes.”

Pipe its response straight into `ai_patch.py`.

---

## License

MIT – do what you want.
