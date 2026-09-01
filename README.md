# Optimized Addons

A Minecraft modpack based on [Fabulously Optimized](https://modrinth.com/modpack/fabulously-optimized), with a quality-of-life addition on top.

This is a small personal pack. It is **not affiliated with or endorsed by the Fabulously Optimized authors**.

## What's in it

Everything Fabulously Optimized ships — performance, rendering and visual improvements — plus:

| Mod | What it does |
| --- | --- |
| [Inventory Profiles Next](https://modrinth.com/mod/inventory-profiles-next) | Sorting for inventories and chests, with hotkeys and per-container profiles |

The mod loader and base pack version for each release are recorded in that release's `pack.toml`.

## Supported versions

Each Minecraft version lives in its own directory at the root of this repository, named after the Minecraft version it targets. Every directory is a self-contained packwiz pack and is published as a separate version on Modrinth.

## Installing

The pack is distributed on Modrinth at [Modrinth project page](https://modrinth.com/modpack/optimized-addons).

## Updating

New versions are published on the same Modrinth project page. Most launchers can update an existing instance in place. Look for an update option in the instance settings.

## Building from source

This repository holds the [packwiz](https://github.com/packwiz/packwiz) metadata, not the mod files themselves. To build a pack yourself, enter the directory for the Minecraft version you want:

```bash
cd <mc-version>
packwiz refresh
packwiz mr export
```

The resulting `.mrpack` can be imported into any launcher that supports the Modrinth pack format.

### Adding a mod

```bash
cd <mc-version>
packwiz mr install <modrinth-slug>
packwiz refresh
```

### Updating mods

```bash
cd <mc-version>
packwiz update --all      # or: packwiz update <mod>
packwiz refresh
```

## Credits

The pack configuration is derived from [Fabulously Optimized](https://github.com/Fabulously-Optimized/fabulously-optimized). Copyright 2020-2026 Fabulously Optimized Authors. The name "Fabulously Optimized" and the names of its contributors are not used to endorse or promote this pack.

Individual mods are the property of their respective authors and are distributed under their own licenses. No mod files are stored in this repository; they are downloaded from Modrinth at install time.

## License

This repository is licensed under the WTFPL — see `LICENSE`.

Exception: the Minecraft version directories are derived from Fabulously Optimized and remain under the BSD 3-Clause License. Each of them contains a `LICENSE.md` with the full text and copyright notice, which ships with every exported pack.
