#!/usr/bin/env python3
"""
flatten.py  –  produce PROJECT_DUMP.md
Usage:  python flatten.py  [--root .] [--out PROJECT_DUMP.md]

Ignores:
  - .gitignore patterns
  - --skip-name  (multiple)
  - --skip-ext   (multiple)
  - --skip-dir   (multiple, basename only)
  - --skip-path  (multiple, absolute or relative, forward slashes)
"""

import argparse, os, re, mimetypes, fnmatch
import subprocess
from pathlib import Path

# ---------- helpers ----------------------------------------------------------
def parse_gitignore(root: Path):
    gitignore = root / '.gitignore'
    if not gitignore.exists():
        return []
    patterns = []
    for line in gitignore.read_text(encoding='utf-8', errors='ignore').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            if line.endswith('/'):
                patterns.append(line.rstrip('/') + '/**')
            else:
                patterns.append(line)
    return patterns

def should_skip(path: Path, root: Path, patterns, args):
    """True if path should be skipped."""
    rel = path.relative_to(root).as_posix()

    # 1. .gitignore
    if any(fnmatch.fnmatch(rel + ('/' if path.is_dir() else ''), p) for p in patterns):
        return True

    # 2. --skip-path (now works for dirs AND files, partial matches)
    for sp in args.skip_path:
        if rel.startswith(sp.rstrip('/')):
            return True

    # 3. Extension globs / basename rules
    if path.is_file():
        # extension globs (e.g. '*.min.js' or '.min.js')
        for pat in args.skip_ext:
            if fnmatch.fnmatch(rel, '*' + pat) or fnmatch.fnmatch(path.name, '*' + pat):
                return True
        # exact basename
        if any(fnmatch.fnmatch(path.name, p) for p in args.skip_name):
            return True

def build_tree(root: Path):
    """Return pretty tree string (like `tree -I`)."""
    try:
        out = subprocess.check_output(
            ['tree', '-n', '--noreport', root], text=True, stderr=subprocess.DEVNULL
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        # fallback
        lines = []
        for dirpath, dirnames, filenames in os.walk(root):
            level = dirpath.replace(str(root), '').count(os.sep)
            indent = '│   ' * level + '├── '
            lines.append(f"{indent}{os.path.basename(dirpath)}/")
            for f in filenames:
                lines.append(f"{indent}{f}")
        out = '\n'.join(lines)
    return out

def dump_file(root: Path, file: Path, patterns, args):
    if should_skip(file, root, patterns, args):
        return None
    try:
        src = file.read_text(encoding='utf-8')
    except Exception as e:
        return f"<!-- error reading {file}: {e} -->"
    rel = file.relative_to(root)
    ext = file.suffix.lower()
    lang = mimetypes.types_map.get(ext, '').split('/')[-1] or ext.lstrip('.')
    return f'<details>\n<summary><code>{rel}</code></summary>\n\n```{lang}\n{src}\n```\n\n</details>\n'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', default='PROJECT_DUMP.md')
    ap.add_argument('--skip-name', action='append', default=[])
    ap.add_argument('--skip-ext', action='append', default=[])
    ap.add_argument('--skip-dir', action='append', default=[])
    ap.add_argument('--skip-path', action='append', default=[])
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    patterns = parse_gitignore(root)
    out_lines = [f"# Flattened project tree for `{root.name}`\n"]
    out_lines.append("```")
    out_lines.append(build_tree(root).strip())
    out_lines.append("```\n")

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dp = Path(dirpath)

        # 1. Skip this directory entirely?
        if should_skip(dp, root, patterns, args):
            dirnames[:] = []
            continue

        # 2. Skip individual files
        for fname in filenames:
            f = dp / fname
            if should_skip(f, root, patterns, args):
                continue
            dumped = dump_file(root, f, patterns, args)
            if dumped:
                out_lines.append(dumped)

    Path(args.out).write_text('\n'.join(out_lines), encoding='utf-8')
    print(f"Wrote {args.out} ({len(out_lines)} lines)")

if __name__ == '__main__':
    main()