<p align="center">
  <img src="assets/icon.png" alt="Starfield Toolkit" width="250" />
</p>
<h1 align="center">Starfield Toolkit</h1>

> **Disclaimer:** Starfield Toolkit is an unofficial, community-built tool. It is **not affiliated with, endorsed by, or sponsored by Bethesda Softworks, ZeniMax Media, or Microsoft**. "Starfield" and "Bethesda" are trademarks of their respective owners; all game assets, creation metadata, and API endpoints remain the property of those rights holders. This project simply provides a convenience UI over publicly accessible information.

> **This tool is designed for Bethesda Creations only.**
> If you use Nexus Mods with a mod manager like Vortex or MO2, those tools already provide load order management, update checking, and more. This project is not intended to replace them.

Starfield Toolkit is a lightweight Windows GUI to help managing official Bethesda Creations content in Starfield.

The sole reason for its existence is that some operations are frustratingly non-user-friendly in-game and on the site, e.g. you have no other way to check for pending updates than walking through all creations in your library one by one.
This toolbox tries to provide solutions to issues like this without messing with the game itself.

# System requirements
1. **Windows**
2. Starfield installed via Steam
3. Using only mods from the Bethesda official creations store

No other options are supported, nor planned.

> **Mods from Nexus or other sources, installed manually or via Vortex/MO2 WILL BREAK the app !**
> It heavily relies on information from the creations pages to do its job, missing that will result in unexpected behaviour


# Download

Grab the latest `StarfieldToolkit.exe` from [Releases](https://github.com/MightyOwl4/starfield-toolkit/releases/latest).

> **Downloading executables from unknown people is generally a bad idea!**
>
> Here, I warned you! :D The EXE file is automatically built by GitHub based on the (public) code in the repo, so unless someone hacks ME and compromises the repo, you should be safe. But ... :D

If you prefer to install and compile yourself - look below

# Documentation

Full documentation — user manual, architecture articles, and reference — is published as a GitHub Pages site:

**→ https://mightyowl4.github.io/starfield-toolkit/**

The source lives under [`docs/`](docs/index.html) and includes:

- **Manual** — tab-by-tab walkthrough of the UI
- **Concepts** — how Auto-Sort works, what rule books are, the sorter priority pipeline, caching, Fast Lane baseline
- **Reference** — file locations, glossary, FAQ, shipped-features index

**Local preview (Docker):**

```bash
cd docs
docker compose up
```

Then open http://localhost:4000/. The container runs Jekyll with the `github-pages` gem (same versions GitHub Pages serves), watches for file changes with polling (works on Windows/WSL), and live-reloads the browser on edit.

# Project setup

You need Python 3.12+ and uv installed
```bash
# Clone the repository
git clone <repo-url>
cd starfield-tool

# Install dependencies
uv sync

# Run the application
uv run python -m starfield_tool
```

# Building

```
make build
```

Produces `build/dist/StarfieldToolkit.exe` via PyInstaller.


# Credits & Acknowledgments

This project builds on the work of the Starfield modding community. Special thanks to:

- **[LOOT](https://loot.github.io/)** — Load Order Optimisation Tool. The Starfield masterlist is used directly for sorting rules and plugin metadata.
- **[hst12/Starfield-Creations-Mod-Manager-and-Catalog-Fixer](https://github.com/hst12/Starfield-Creations-Mod-Manager-and-Catalog-Fixer)** — Research reference for ContentCatalog and Plugins.txt handling.
- **[monster-cookie/starfield-modding-notes](https://github.com/monster-cookie/starfield-modding-notes)** — Community documentation on load order tiers and plugin types.
- **[Ortham's Load Order in Starfield](https://blog.ortham.net/posts/2024-06-28-load-order-in-starfield/)** — Detailed technical writeup on how Starfield's load order works.
- **[\[XSX\] Starfield Load Orders](https://docs.google.com/spreadsheets/d/1WmuMojgCHmYzgFCVAafFA2Mxs43kcwkhN_BgagBXuRk/)** — Community spreadsheet with the 11-tier category system used for auto sorting.
- **[Bethesda Creations](https://creations.bethesda.net/)** — The platform whose (undocumented) API powers the update and achievement checks.

# AI usage disclosure

## App logo

Logo is produced by Midjourney, using the following prompt:

> Minimalist app icon design, a mechanic wrench lying horizontally centered inside a thin white circular ring with a small gaps at left and right side (Starfield logo circle style), the wrench handle and left half of the head painted with vintage retro racing stripes in red orange yellow blue and cyan running along its length, right side plain brushed metal, solid dark space navy background, clean vector icon style, no gradients, square format
>
This project has no budget to commission an artist, however anyone willing to contribute a decent human-made one is more than welcome.


## Code

Produced mostly by Anthropic's Opus 4.6, using spec-driven development approach, and passing code review to ensure there are no (major) flops.

# License

See [LICENSE](LICENSE) for details (but It's MIT, so why bother)
