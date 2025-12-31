# **CodeFlatter**

A tiny pair of Python scripts that

1. **flatten** a project folder into a single markdown report  
2. let an LLM (or you) **patch the project back** by pasting blocks into stdin

## **Installation**

No packages to install—just drop the two files anywhere in your $PATH (or side-by-side in the repo).

chmod \+x flatten.py ai\_patch.py

## **flatten.py**

Generate a self-contained PROJECT\_DUMP.md file with

* a directory tree  
* collapsible \<details\> blocks that contain the full source of every file you *didn’t* exclude

### **Quick start**

python flatten.py \--root ./my-project \--out PROJECT\_DUMP.md

### **Options & Filtering**

You can skip files using .gitignore (default), custom ignore files, or command-line flags. Arguments support multiple flags or comma-separated lists.

| flag | meaning | example |
| :---- | :---- | :---- |
| \--skip-name | exact basename | README.md or config.json,secrets.yaml |
| \--skip-ext | extension wildcard | .min.js or .map,.css |
| \--skip-dir | directory basename | node\_modules or venv,build,dist |
| \--skip-path | relative path | dist/\*\* |
| \--no-gitignore | Ignore .gitignore file | (flag) |
| \--ignore-file | Use custom ignore file | .my\_custom\_ignore |
| \--line-numbers | Add line numbers to code | (flag) |

**Examples:**

Skip common build artifacts (comma-separated):

python flatten.py \--skip-path dist,node\_modules,assets/images

Ignore .gitignore rules but load a custom list:

python flatten.py \--no-gitignore \--ignore-file .llm\_ignore

## **ai\_patch.py**

Paste (or pipe) a block like the one below into the script; it applies the diff or full-file replacement and writes the changes to disk.

**Usage:**

cat patches.txt | python ai\_patch.py \[--dry-run\]

*\--dry-run only prints what would change.*

### **Supported Formats**

**1\. Whole-file replacement:**

\#\# replace-start: src/main.js  
// entire new contents here  
\#\# replace-end

**2\. Unified Diff (saves tokens):**

\#\# patch-start: src/utils.py  
\--- src/utils.py  
\+++ src/utils.py  
@@ \-5,7 \+5,9 @@  
\- old line  
\+ new line  
\#\# patch-end

**3\. Deletion:**

\#\# delete: tmp/leftovers.json

## **Tips for LLM prompting**

After you send PROJECT\_DUMP.md, you can ask the model:

“Return only the blocks \#\# replace-start, \#\# patch-start, or \#\# delete: that are needed to apply the requested changes.”

Pipe its response straight into ai\_patch.py.

## **License**

MIT – do what you want.
