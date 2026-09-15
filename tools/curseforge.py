#!/usr/bin/env python3
"""Maintain the [update.curseforge] block of packwiz metafiles.

Project data comes from CFWidget, a public cache that needs no API key.

    sync    refresh every file id, matched by the recorded filename
    link    attach CurseForge metadata to a mod that has none yet
    adopt   copy project ids from another pack directory

Usage:
    tools/curseforge.py <pack-dir> sync [--check] [--jobs N]
    tools/curseforge.py <pack-dir> link <url-or-slug> [--target NAME]
    tools/curseforge.py <pack-dir> adopt <source-pack-dir> [--check]

Exit status: 0 on success, 1 on anything left unresolved or, for
`sync --check`, on any stale id.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import re
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.cfwidget.com"
DEFAULT_CLASS = "minecraft/mc-mods"
SUBDIRS = ("mods", "resourcepacks")
SECTION = "[update.curseforge]"
USER_AGENT = "packwiz-curseforge-sync/2.0"
FILE_ID_RE = re.compile(r"^file-id\s*=\s*\d+\s*$", re.MULTILINE)

TIMEOUT = 25
DEADLINE = 45
ATTEMPTS = 4
BACKOFF = 1.5
DEFAULT_JOBS = 8
QUEUED_STATUS = 202


class CFWidget:
    """Read-only client for the public CurseForge cache."""

    def project(self, key: str | int) -> dict:
        request = urllib.request.Request(
            f"{API_BASE}/{str(key).lstrip('/')}",
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        )
        last: object = "no attempt made"
        expires = time.monotonic() + DEADLINE

        for attempt in range(ATTEMPTS):
            if attempt:
                time.sleep(BACKOFF * attempt)
            remaining = expires - time.monotonic()
            if remaining <= 0:
                break
            try:
                with urllib.request.urlopen(
                        request, timeout=min(TIMEOUT, remaining)) as response:
                    # 202 means the project is being fetched; retry.
                    if response.status != QUEUED_STATUS:
                        return json.load(response)
                last = "queued"
            except urllib.error.HTTPError as exc:
                if 400 <= exc.code < 500 and exc.code != 429:
                    raise
                last = exc
            except (http.client.HTTPException, OSError, ValueError) as exc:
                last = exc

        raise urllib.error.URLError(f"gave up: {last}")

    def projects(self, keys: list[str], jobs: int) -> dict[str, dict | Exception]:
        """Fetch several projects concurrently, reporting progress on stderr."""
        results: dict[str, dict | Exception] = {}
        total = len(keys)

        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            pending = {pool.submit(self.project, key): key for key in keys}
            outstanding = set(keys)

            for done, future in enumerate(
                    concurrent.futures.as_completed(pending), start=1):
                key = pending[future]
                try:
                    results[key] = future.result()
                except Exception as exc:
                    results[key] = exc
                outstanding.discard(key)

                waiting = ""
                if 0 < len(outstanding) <= 3:
                    waiting = f" (waiting on {', '.join(sorted(outstanding))})"
                print(f"\r\033[K  resolving {done}/{total}{waiting}", end="",
                      file=sys.stderr, flush=True)

        if total:
            print(file=sys.stderr)
        return results


def normalise(filename: str) -> str:
    """CurseForge stores spaces as plus signs."""
    return filename.replace("+", " ").casefold()


def find_file_id(project: dict, filename: str) -> int | None:
    target = normalise(filename)
    for entry in project.get("files", []):
        if normalise(str(entry.get("name", ""))) == target:
            return int(entry["id"])
    return None


def project_path(reference: str) -> str:
    """Turn a project URL or bare slug into a CFWidget lookup path."""
    if "://" in reference:
        return urllib.parse.urlparse(reference).path.strip("/")
    return f"{DEFAULT_CLASS}/{reference.strip('/')}"


def split_section(text: str, header: str) -> tuple[str, str | None]:
    """Split a top-level TOML table out of `text`."""
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


def metafiles(pack_dir: Path) -> list[Path]:
    found: list[Path] = []
    for subdir in SUBDIRS:
        found.extend(sorted((pack_dir / subdir).glob("*.pw.toml")))
    return found


def curseforge_block(data: dict) -> dict:
    return data.get("update", {}).get("curseforge", {})


def run_sync(client: CFWidget, pack_dir: Path, check: bool, jobs: int) -> int:
    updated: list[str] = []
    current: list[str] = []
    unlinked: list[str] = []
    failed: list[tuple[str, str]] = []

    pending: list[tuple[Path, str, str, str]] = []
    for path in metafiles(pack_dir):
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        project_id = curseforge_block(data).get("project-id")
        filename = data.get("filename")

        if project_id is None:
            unlinked.append(path.as_posix())
            continue
        if not filename:
            failed.append((path.as_posix(), "no filename field"))
            continue

        pending.append((path, text, str(project_id), filename))

    projects = client.projects(sorted({p for _, _, p, _ in pending}), jobs)

    for path, text, project_id, filename in pending:
        project = projects.get(project_id)

        if isinstance(project, Exception):
            failed.append((path.as_posix(),
                           f"lookup failed for {project_id}: {project}"))
            continue

        file_id = find_file_id(project, filename)
        if file_id is None:
            failed.append((path.as_posix(), f"no CurseForge file named {filename}"))
            continue

        old_file_id = curseforge_block(tomllib.loads(text)).get("file-id")
        if file_id == old_file_id:
            current.append(path.as_posix())
            continue

        updated.append(f"{path.as_posix()}: {old_file_id} -> {file_id}")
        if not check:
            path.write_text(
                FILE_ID_RE.sub(f"file-id = {file_id}", text, count=1),
                encoding="utf-8",
            )

    verb = "stale" if check else "updated"
    print(f"{verb}: {len(updated)}  current: {len(current)}  "
          f"unlinked: {len(unlinked)}  failed: {len(failed)}")

    if updated:
        print()
        for line in updated:
            print(f"  {line}")

    if unlinked:
        print("\nno CurseForge metadata, run `make link` for these:")
        for rel in unlinked:
            print(f"  {rel}")

    if failed:
        print("\nunresolved:")
        for rel, reason in failed:
            print(f"  {rel}: {reason}")

    if failed or unlinked:
        return 1
    return 1 if (check and updated) else 0


def pick_target(pack_dir: Path, target: str | None) -> Path | list[Path]:
    """Return the metafile to link, or the candidates when it is ambiguous."""
    if target is not None:
        stem = target.removesuffix(".pw.toml")
        matches = [p for p in metafiles(pack_dir) if p.name == f"{stem}.pw.toml"]
        return matches[0] if len(matches) == 1 else matches

    candidates = [
        path for path in metafiles(pack_dir)
        if not curseforge_block(tomllib.loads(path.read_text(encoding="utf-8")))
    ]
    return candidates[0] if len(candidates) == 1 else candidates


def run_link(client: CFWidget, pack_dir: Path,
             reference: str, target: str | None) -> int:
    chosen = pick_target(pack_dir, target)

    if isinstance(chosen, list):
        if not chosen:
            print("error: no metafile to link; every mod already has "
                  "CurseForge metadata", file=sys.stderr)
        else:
            print("error: several metafiles lack CurseForge metadata, "
                  "pass --target to pick one:", file=sys.stderr)
            for path in chosen:
                print(f"  {path.name.removesuffix('.pw.toml')}", file=sys.stderr)
        return 2

    path = project_path(reference)
    try:
        project = client.project(path)
    except (http.client.HTTPException, OSError, ValueError) as exc:
        print(f"error: lookup failed for {path}: {exc}", file=sys.stderr)
        return 1

    project_id = project.get("id")
    if project_id is None:
        print(f"error: no CurseForge project at {path}", file=sys.stderr)
        return 1

    text = chosen.read_text(encoding="utf-8")
    filename = tomllib.loads(text).get("filename")
    if not filename:
        print(f"error: {chosen} has no filename field", file=sys.stderr)
        return 1

    file_id = find_file_id(project, filename)
    if file_id is None:
        print(f"error: project {path} has no file named {filename}",
              file=sys.stderr)
        print("the platforms may ship different builds; check the file list "
              "on CurseForge", file=sys.stderr)
        return 1

    base, _ = split_section(text, SECTION)
    chosen.write_text(
        f"{base.rstrip(chr(10))}\n\n{SECTION}\n"
        f"file-id = {file_id}\nproject-id = {project_id}\n",
        encoding="utf-8",
    )
    print(f"linked {chosen.as_posix()} to {path} ({project_id}/{file_id})")
    return 0


def run_adopt(pack_dir: Path, source_dir: Path, check: bool) -> int:
    """Copy project ids from metafiles of the same name in another pack."""
    if not (source_dir / "pack.toml").is_file():
        print(f"error: no pack.toml in {source_dir}/", file=sys.stderr)
        return 2

    known: dict[str, int] = {}
    for path in metafiles(source_dir):
        project_id = curseforge_block(
            tomllib.loads(path.read_text(encoding="utf-8"))).get("project-id")
        if project_id is not None:
            known[path.name] = int(project_id)

    if not known:
        print(f"error: no project ids found in {source_dir}/", file=sys.stderr)
        return 2

    adopted: list[str] = []
    linked: list[str] = []
    missing: list[str] = []

    for path in metafiles(pack_dir):
        text = path.read_text(encoding="utf-8")
        if curseforge_block(tomllib.loads(text)):
            linked.append(path.as_posix())
            continue

        project_id = known.get(path.name)
        if project_id is None:
            missing.append(path.as_posix())
            continue

        adopted.append(f"{path.as_posix()} -> {project_id}")
        if not check:
            base, _ = split_section(text, SECTION)
            path.write_text(
                f"{base.rstrip(chr(10))}\n\n{SECTION}\n"
                f"file-id = 0\nproject-id = {project_id}\n",
                encoding="utf-8",
            )

    verb = "would adopt" if check else "adopted"
    print(f"{verb}: {len(adopted)}  already linked: {len(linked)}  "
          f"not in {source_dir}: {len(missing)}")

    if adopted:
        print()
        for line in adopted:
            print(f"  {line}")
        if not check:
            print("\nfile ids are placeholders, run sync next")

    if missing:
        print("\nno match in the source pack, run `make link` for these:")
        for rel in missing:
            print(f"  {rel}")

    if check and adopted:
        return 1
    return 1 if missing else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pack_dir", type=Path, help="pack directory, e.g. 26.2")

    modes = parser.add_subparsers(dest="mode", required=True)

    sync = modes.add_parser("sync", help="refresh every file id")
    sync.add_argument("--check", action="store_true",
                      help="report stale ids without writing")
    sync.add_argument("--jobs", type=int, default=DEFAULT_JOBS,
                      help=f"concurrent requests (default: {DEFAULT_JOBS})")

    link = modes.add_parser("link", help="attach metadata to one mod")
    link.add_argument("reference", help="CurseForge project URL or slug")
    link.add_argument("--target", default=None,
                      help="metafile name, when more than one is unlinked")

    adopt = modes.add_parser("adopt", help="copy project ids from another pack")
    adopt.add_argument("source", type=Path, help="source pack, e.g. 26.2")
    adopt.add_argument("--check", action="store_true",
                       help="report what would be copied without writing")

    args = parser.parse_args()

    pack_dir: Path = args.pack_dir
    if not (pack_dir / "pack.toml").is_file():
        print(f"error: no pack.toml in {pack_dir}/", file=sys.stderr)
        return 2
    if not metafiles(pack_dir):
        print(f"error: no metafiles found under {pack_dir}/", file=sys.stderr)
        return 2

    if args.mode == "adopt":
        return run_adopt(pack_dir, args.source, args.check)

    client = CFWidget()

    if args.mode == "sync":
        return run_sync(client, pack_dir, args.check, args.jobs)
    return run_link(client, pack_dir, args.reference, args.target)


if __name__ == "__main__":
    raise SystemExit(main())
