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

PATCH_START_RE   = re.compile(r'^##\s*patch-start:\s*([^\s]+)', re.I)
REPLACE_START_RE = re.compile(r'^##\s*replace-start:\s*([^\s]+)', re.I)
DELETE_RE        = re.compile(r'^##\s*delete:\s*([^\s]+)', re.I)
END_RE           = re.compile(r'^##\s*(patch|replace)-end', re.I)
HUNK_HEADER_RE   = re.compile(r'^@@\s-(\d+)(?:,(\d+))?\s\+(\d+)(?:,(\d+))?\s@@')

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

def apply_diff(diff_text, path: Path, dry):
    """Applies a unified diff to the file at path."""
    if not path.exists():
        # If the file doesn't exist, we assume it's being created (like /dev/null in git diffs)
        print(f"📄 {path} does not exist; treating as empty file.")
        original_lines = []
    else:
        original_lines = path.read_text(encoding='utf-8').splitlines(keepends=True)

    try:
        new_lines = apply_unified_diff_logic(original_lines, diff_text)
    except Exception as e:
        print(f"❌ Failed to apply diff to {path}: {e}")
        return

    if dry:
        print(f"[dry-run] would patch {path} (result: {len(new_lines)} lines)")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(new_lines), encoding='utf-8')
        print(f"Patched {path}")

def apply_unified_diff_logic(original_lines, patch_text):
    """
    Parses and applies a unified diff to a list of lines.
    Returns the new list of lines.
    """
    patch_lines = patch_text.splitlines(keepends=True)
    output = []
    src_idx = 0
    
    i = 0
    while i < len(patch_lines):
        line = patch_lines[i]
        
        # Skip header lines usually found in git diffs
        if line.startswith('---') or line.startswith('+++') or line.startswith('index '):
            i += 1
            continue
            
        m = HUNK_HEADER_RE.match(line)
        if not m:
            # If it's not a hunk header and we haven't started patching, just skip (garbage or comments)
            i += 1
            continue

        # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
        old_start = int(m.group(1))
        # old_count = int(m.group(2)) if m.group(2) else 1
        
        # Calculate where we should be in the source file
        # Diff line numbers are 1-based.
        target_src_idx = old_start - 1 if old_start > 0 else 0
        
        # Sanity check: Are we going backwards?
        if target_src_idx < src_idx:
             raise ValueError(f"Hunk at line {i} attempts to patch earlier in file than previous hunk.")
             
        # Copy original lines up to the start of this hunk (preserve unchanged parts)
        output.extend(original_lines[src_idx:target_src_idx])
        src_idx = target_src_idx
        
        i += 1 # Move past the @@ header
        
        # Process the hunk body
        while i < len(patch_lines):
            pl = patch_lines[i]
            if HUNK_HEADER_RE.match(pl):
                break # Start of next hunk
            
            # Common git diff markers
            if pl.startswith(' '):
                # Context line: keep original
                if src_idx < len(original_lines):
                    # In a strict patcher, we would verify original_lines[src_idx] == pl[1:]
                    output.append(original_lines[src_idx])
                src_idx += 1
            elif pl.startswith('-'):
                # Deletion: skip original
                src_idx += 1
            elif pl.startswith('+'):
                # Addition: add from patch
                output.append(pl[1:])
            elif pl.startswith('\\'):
                # "\ No newline at end of file" - ignore
                pass
            elif pl.strip() == '':
                 # Sometimes empty lines in patches lose their leading space? 
                 # We treat purely empty lines as context if appropriate, or ignore.
                 pass
            else:
                # Unexpected line inside hunk; might be end of hunk logic if fuzzy
                # For now, we assume it breaks the hunk if it doesn't start with space/+/-
                # But typically valid diffs adhere strictly.
                break 

            i += 1
            
    # Copy any remaining lines from the original file
    output.extend(original_lines[src_idx:])
    return output

def write_file(text_block, path: Path, dry):
    if dry:
        print(f"[dry-run] would write {len(text_block)} chars to {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(text_block), encoding='utf-8')
        print(f"Wrote {path}")

def delete_file(path: Path, dry):
    if dry:
        print(f"[dry-run] would delete {path}")
    else:
        if path.exists():
            path.unlink()
            print(f"Deleted {path}")
        else:
            print(f"Skipped delete (not found): {path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help="Don't actually write files")
    args = parser.parse_args()
    
    # Read from stdin (pipe)
    input_text = sys.stdin.read()
    if not input_text.strip():
        print("No input provided. Pipe a patch file into this script.")
        print("Example: cat changes.txt | python ai_patch.py")
        sys.exit(0)

    apply_patches(input_text, Path('.').resolve(), dry=args.dry_run)