# Optimized Addons

A Minecraft modpack based on [Fabulously Optimized](https://modrinth.com/modpack/fabulously-optimized), with a quality-of-life addition on top.

It is **not affiliated with or endorsed by the Fabulously Optimized authors**.

## What's in it

Everything Fabulously Optimized ships, plus:

- Inventory Profiles Next
- Xaero's Minimap

## Supported versions

This modpack works on Minecraft Java Edition for these versions:

- 26.2

## Installing

I'm currently working on publishing this modpack on Modrinth and CurseForge.

<!--## Updating-->

## Building from source

This repository holds the [packwiz](https://github.com/packwiz/packwiz) metadata, not the mod files themselves.

Requirements: `packwiz`, `make`, `unzip`, and Python 3.11 or later.

```bash
make build V=<mc-version>
```

Artifacts land in `<mc-version>/build/`, named `<mc-version>-<pack-version>`:

- the `.mrpack` imports into any launcher supporting the Modrinth pack format
- the `.zip` imports into any launcher supporting the CurseForge pack format

`build` also runs `make check`, which verifies that no mod was bundled as a raw jar and that every metafile has a matching entry in both archives.

## Working on the pack

Every metafile carries two providers: `[update.modrinth]`, written by packwiz,
and `[update.curseforge]`, maintained by `tools/curseforge.py` through
[CFWidget](https://www.cfwidget.com/). The Makefile targets keep the two in
step, so prefer them over raw `packwiz` commands.

### Updating mods

```bash
make update V=<mc-version>
```

Updates every mod and realigns the CurseForge file ids. Use `make sync V=<mc-version>` to realign the ids on their own, after reverting a mod by hand.

### Adding a mod

```bash
make add V=<mc-version> MR=<modrinth-slug> CF=<curseforge-project-url or curseforge-slug>
```

The CurseForge slug often differs from the Modrinth one.

### Linking an existing mod

```bash
make link V=<mc-version> CF=<curseforge-project-url> [TARGET=<metafile>]
```

Attaches CurseForge metadata to a mod already in the pack, leaving its version alone. `TARGET` is the metafile name without the extension, needed only when more than one mod is unlinked.

Do not use `make add` for this: `packwiz mr add` would bump the mod to its
latest version.

### Starting a new Minecraft version

```bash
make adopt V=<new-version> FROM=<existing-version>
make sync V=<new-version>
```

`adopt` copies the CurseForge project ids from metafiles of the same name, then `sync` resolves the file ids. Mods with no counterpart in the source pack are listed and need `make link`.

### Releasing

```bash
make release-push V=<mc-version> TAG=<x.y.z>
```

Writes the tag into `pack.toml`, builds, commits, tags, and pushes. Requires a clean working tree.

## Credits

The pack configuration is derived from [Fabulously Optimized](https://github.com/Fabulously-Optimized/fabulously-optimized). Copyright 2020-2026 Fabulously Optimized Authors. The name "Fabulously Optimized" and the names of its contributors are not used to endorse or promote this pack.

Individual mods are the property of their respective authors and are distributed under their own licenses. No mod files are stored in this repository; they are downloaded from Modrinth at install time.

## License

This repository is licensed under the CC0 Universal — see `LICENSE`.

Exception: the Minecraft version directories are derived from Fabulously Optimized and remain under the BSD 3-Clause License. Each of them contains a `LICENSE.md` with the full text and copyright notice, which ships with every exported pack.
