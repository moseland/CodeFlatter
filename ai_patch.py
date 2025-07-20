#!/usr/bin/env python3
"""
ai_patch.py – apply AI-generated patches from stdin or a file.

Patch blocks look like:

## patch-start: path/to/file.py
--- path/to/file.py
+++ path/to/file.py
@@ -3,7 +3,9 @@
 ...
## patch-end

OR, for whole-file replacements:

## replace-start: path/to/file.py
<entire new contents>
## replace-end

OR, for deletions:

## delete: path/to/file.py
"""

import sys, re, os, argparse
from pathlib import Path

PATCH_START_RE  = re.compile(r'^##\s*patch-start:\s*([^\s]+)', re.I)
REPLACE_START_RE = re.compile(r'^##\s*replace-start:\s*([^\s]+)', re.I)
DELETE_RE       = re.compile(r'^##\s*delete:\s*([^\s]+)', re.I)
END_RE          = re.compile(r'^##\s*(patch|replace)-end', re.I)

def apply_patches(text: str, root: Path, dry=False):
    lines = text.splitlines(keepends=True)
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if (m := PATCH_START_RE.match(line)):
            path = root / m.group(1)
            block, idx = read_until(lines, idx + 1, END_RE)
            apply_diff(block, path, dry)
        elif (m := REPLACE_START_RE.match(line)):
            path = root / m.group(1)
            block, idx = read_until(lines, idx + 1, END_RE)
            write_file(block, path, dry)
        elif (m := DELETE_RE.match(line)):
            path = root / m.group(1)
            delete_file(path, dry)
            idx += 1
        else:
            idx += 1

def read_until(lines, start, end_re):
    """Return (block, next_idx)"""
    block = []
    for i in range(start, len(lines)):
        if end_re.match(lines[i]):
            return ''.join(block), i + 1
        block.append(lines[i])
    raise ValueError("Unterminated patch block")

def apply_diff(diff_lines, path: Path, dry):
    """Crude unified-diff applier using built-in `difflib`."""
    import difflib
    if not path.exists():
        print(f"⚠️  {path} does not exist; creating empty file")
        old = []
    else:
        old = path.read_text(encoding='utf-8').splitlines(keepends=True)
    new = list(difflib.unified_diff(old, [], fromfile=str(path), tofile=str(path), lineterm=''))
    patch = difflib.unified_diff(old, [], fromfile=str(path), tofile=str(path))
    raise NotImplementedError("diff apply not implemented; please use replace blocks")

def write_file(text_block, path: Path, dry):
    if dry:
        print(f"[dry-run] would write {len(text_block)} chars to {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(text_block), encoding='utf-8