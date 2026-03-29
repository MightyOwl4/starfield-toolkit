<p align="center">
  <img src="assets/icon.png" alt="Starfield Toolkit" width="250" />
</p>
<h1 align="center">Starfield Toolkit</h1>

> **This tool is designed for Bethesda Creations only.**
> If you use Nexus Mods with a mod manager like Vortex or MO2, those tools already provide load order management, update checking, and more. This project is not intended to replace them.

Starfield Toolkit is a lightweight Windows GUI to help managing official Bethesda Creations content in Starfield.

The sole reason for its existence is that some operations are frustratingly non-user-friendly in-game and on the site, e.g. you have no other way to check for pending updates than walking through all creations in your library one by one.
This toolbox tries to provide solutions to issues like this without messing with the game itself.

## Download

Grab the latest `StarfieldToolkit.exe` from [Releases](https://github.com/MightyOwl4/starfield-toolkit/releases/latest).

> **Downloading executables from unknown people is generally a bad idea!**
>
> Here, I warned you! :D The EXE file is automatically built by GitHub based on the (public) code in the repo, so unless someone hacks ME and compromises the repo, you should be safe. But ... :D

If you prefer to install and compile yourself - look below

## Tools

### Installed Creations

View all installed Bethesda Creations in their current load order. Features:

#### Check for Updates
compares your installed versions against the Bethesda Creations API and highlights outdated entries
![check_for_updates.png](assets/check_for_updates.png)


#### Check Achievements
flags any creations that will disable achievements when active
![check-achievement-diabling.png](assets/check-achievement-diabling.png)

#### Export
save your creation list as a markdown table or CSV, for sharing online

#### Auto-refresh
watches your Plugins.txt and ContentCatalog.txt for changes and prompts you to reload


## Project setup

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

## Building

```
make build
```

Produces `build/dist/StarfieldToolkit.exe` via PyInstaller.


## AI usage disclosure

### App log

Logo is produced by Midjourney, using the following prompt:

> Minimalist app icon design, a mechanic wrench lying horizontally centered inside a thin white circular ring with a small gaps at left and right side (Starfield logo circle style), the wrench handle and left half of the head painted with vintage retro racing stripes in red orange yellow blue and cyan running along its length, right side plain brushed metal, solid dark space navy background, clean vector icon style, no gradients, square format
>
This project has no budget to commission an artist, however anyone willing to contribute a decent human-made one is more than welcome.


### Code

Produced mostly by Anthropic's Opus 4.6, using spec-driven development approach, and passing code review to ensure there are no (major) flops.

## License

See [LICENSE](LICENSE) for details (but It's MIT, so why bother)
