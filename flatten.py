#!/usr/bin/env python3
"""
flatten.py:  produce PROJECT_DUMP.md
Usage:  python flatten.py  [--root .] [--out PROJECT_DUMP.md] [--no-gitignore] [--ignore-file FILE]

Ignores:
  - .gitignore patterns (unless --no-gitignore is set)
  - patterns in --ignore-file (if provided)
  - --skip-name  (multiple, supports comma-separated)
  - --skip-ext   (multiple, supports comma-separated)
  - --skip-dir   (multiple, basename only, supports comma-separated)
  - --skip-path  (multiple, absolute or relative, supports comma-separated)
"""

import argparse, os, re, mimetypes, fnmatch
import subprocess
from pathlib import Path

# ---------- helpers -----------
def read_ignore_patterns(path: Path):
    """Read patterns from a file, similar to .gitignore format."""
    if not path.exists():
        return []
    patterns = []
    try:
        content = path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return []

    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            if line.endswith('/'):
                patterns.append(line.rstrip('/') + '/**')
            else:
                patterns.append(line)
    return patterns

def get_active_patterns(root: Path, args):
    """Collect all ignore patterns from .gitignore (if active) and custom files."""
    patterns = []
    
    if not args.no_gitignore:
        patterns.extend(read_ignore_patterns(root / '.gitignore'))
    
    if args.ignore_file:
        custom_path = Path(args.ignore_file)
        if not custom_path.is_absolute():
            custom_path = root / custom_path
        if custom_path.exists():
            print(f"Loaded ignore patterns from {custom_path.name}")
            patterns.extend(read_ignore_patterns(custom_path))
            
    return patterns

def should_skip(path: Path, root: Path, patterns, args):
    """True if path should be skipped."""
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return True

    if any(fnmatch.fnmatch(rel + ('/' if path.is_dir() else ''), p) for p in patterns):
        return True

    for sp in args.skip_path:
        if rel.startswith(sp.rstrip('/')):
            return True

    if path.is_file():
        for pat in args.skip_ext:
            if fnmatch.fnmatch(rel, '*' + pat) or fnmatch.fnmatch(path.name, '*' + pat):
                return True
        if any(fnmatch.fnmatch(path.name, p) for p in args.skip_name):
            return True
            
    if path.is_dir():
         if any(fnmatch.fnmatch(path.name, p) for p in args.skip_dir):
            return True

def build_tree(root: Path):
    """Return pretty tree string (like `tree -I`)."""
    try:
        out = subprocess.check_output(
            ['tree', '-n', '--noreport', root], text=True, stderr=subprocess.DEVNULL
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
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
        return f""
    rel = file.relative_to(root)
    ext = file.suffix.lower()
    lang = mimetypes.types_map.get(ext, '').split('/')[-1] or ext.lstrip('.')
    return f'<details>\n<summary><code>{rel}</code></summary>\n\n```{lang}\n{src}\n```\n\n</details>\n'

def normalize_args(arg_list):
    """Splits comma-separated arguments into a flat list."""
    if not arg_list:
        return []
    flat = []
    for item in arg_list:
        flat.extend([x.strip() for x in item.split(',') if x.strip()])
    return flat

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', default='PROJECT_DUMP.md')
    ap.add_argument('--skip-name', action='append', default=[])
    ap.add_argument('--skip-ext', action='append', default=[])
    ap.add_argument('--skip-dir', action='append', default=[])
    ap.add_argument('--skip-path', action='append', default=[])
    ap.add_argument('--no-gitignore', action='store_true', help="Do not use .gitignore for patterns")
    ap.add_argument('--ignore-file', help="Path to a custom file containing ignore patterns")
    
    args = ap.parse_args()
    args.skip_name = normalize_args(args.skip_name)
    args.skip_ext = normalize_args(args.skip_ext)
    args.skip_dir = normalize_args(args.skip_dir)
    args.skip_path = normalize_args(args.skip_path)

    root = Path(args.root).expanduser().resolve()
    patterns = get_active_patterns(root, args)
    
    out_lines = [f"# Flattened project tree for `{root.name}`\n"]
    out_lines.append("```")
    out_lines.append(build_tree(root).strip())
    out_lines.append("```\n")

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dp = Path(dirpath)

        if should_skip(dp, root, patterns, args):
            dirnames[:] = []
            continue

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