#!/usr/bin/env python3
"""Reapply Modrinth metadata after `packwiz curseforge detect`.

`detect` rewrites each metafile to be downloaded from CurseForge: it
replaces the [download] block with `mode = "metadata:curseforge"` and drops
[update.modrinth]. The only part worth keeping is the CurseForge
project/file id pair.

This script extracts that pair from the working tree and reapplies it on top
of the committed version of the metafile, so each one ends up with both
providers:

    [download]           from git  -> direct CDN link in the .mrpack
    [update.modrinth]    from git  -> Modrinth update checks
    [update.curseforge]  from detect -> manifest entry in the CurseForge zip

Run it from the repository root, right after `detect` and before `refresh`.

Usage:
    tools/restore-modrinth.py <pack-dir> [--ref REF] [--check]

Exit status: 0 on success, 1 if any metafile is missing CurseForge metadata
or, with --check, if any metafile would be modified.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SECTION = "[update.curseforge]"
SUBDIRS = ("mods", "resourcepacks")


def split_section(text: str, header: str) -> tuple[str, str | None]:
    """Split a top-level TOML table out of `text`.

    Returns the text without that table, plus the table itself (or None).
    """
    kept: list[str] = []
    section: list[str] = []
    inside = False

    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == header:
            inside = True
            section.append(line)
            continue
        if inside:
            if stripped.startswith("[") and stripped.endswith("]"):
                inside = False
            else:
                section.append(line)
                continue
        kept.append(line)

    return "".join(kept), ("".join(section) if section else None)


def git_show(ref: str, path: str) -> str | None:
    """Return the contents of `path` at `ref`, or None if it is not tracked."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def metafiles(pack_dir: Path) -> list[Path]:
    found: list[Path] = []
    for subdir in SUBDIRS:
        found.extend(sorted((pack_dir / subdir).glob("*.pw.toml")))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pack_dir", type=Path, help="pack directory, e.g. 1.21.1")
    parser.add_argument("--ref", default="HEAD", help="git ref to restore from")
    parser.add_argument("--check", action="store_true",
                        help="report changes without writing")
    args = parser.parse_args()

    pack_dir: Path = args.pack_dir
    if not (pack_dir / "pack.toml").is_file():
        print(f"error: no pack.toml in {pack_dir}/", file=sys.stderr)
        return 2

    targets = metafiles(pack_dir)
    if not targets:
        print(f"error: no metafiles found under {pack_dir}/", file=sys.stderr)
        return 2

    restored: list[str] = []
    unchanged: list[str] = []
    untracked: list[str] = []
    no_curseforge: list[str] = []

    for path in targets:
        rel = path.as_posix()
        current = path.read_text(encoding="utf-8")

        _, curseforge = split_section(current, SECTION)
        if curseforge is None:
            no_curseforge.append(rel)
            continue

        committed = git_show(args.ref, rel)
        if committed is None:
            untracked.append(rel)
            continue

        base, _ = split_section(committed, SECTION)
        merged = f"{base.rstrip(chr(10))}\n\n{curseforge.rstrip(chr(10))}\n"

        if merged == current:
            unchanged.append(rel)
            continue

        restored.append(rel)
        if not args.check:
            path.write_text(merged, encoding="utf-8")

    verb = "would restore" if args.check else "restored"
    print(f"{verb}: {len(restored)}  unchanged: {len(unchanged)}  "
          f"untracked: {len(untracked)}  no CurseForge id: {len(no_curseforge)}")

    if untracked:
        print("\nnot in git, left untouched:")
        for rel in untracked:
            print(f"  {rel}")

    if no_curseforge:
        print("\nno [update.curseforge], will be bundled into overrides/:")
        for rel in no_curseforge:
            print(f"  {rel}")

    if no_curseforge:
        return 1
    if args.check and restored:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
