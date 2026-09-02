# Optimized Addons

A Minecraft modpack based on [Fabulously Optimized](https://modrinth.com/modpack/fabulously-optimized), with a quality-of-life addition on top.

This is a small personal pack. It is **not affiliated with or endorsed by the Fabulously Optimized authors**.

## What's in it

Everything Fabulously Optimized ships, plus:

- Inventory Profiles Next
- Xaero's Minimap

## Supported versions

This modpack works on Minecraft Java Edition for these versions:

- 26.2

## Installing

I'm currently working on publish this modpack on Modrinth and Curseforge.

<!--## Updating-->

## Building from source

This repository holds the [packwiz](https://github.com/packwiz/packwiz) metadata, not the mod files themselves. To build a pack yourself, enter the directory for the Minecraft version you want:

```bash
cd <mc-version>
packwiz refresh
```

then:

```bash
packwiz mr export
```

the resulting `.mrpack` can be imported into any launcher that supports the Modrinth pack format.

Or:

```bash
packwiz cf export --side client
```

the resulting `.zip` can be imported into any launcher that supports the Curseforge pack format.

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

This repository is licensed under the CC0 Universal — see `LICENSE`.

Exception: the Minecraft version directories are derived from Fabulously Optimized and remain under the BSD 3-Clause License. Each of them contains a `LICENSE.md` with the full text and copyright notice, which ships with every exported pack.
