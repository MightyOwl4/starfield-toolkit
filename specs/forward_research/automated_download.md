# Forward Research: Automated Download of Starfield Creations

**Date:** 2026-03-30
**Status:** Research only — not planned for implementation

## Summary

Investigated whether it's possible to programmatically download and install a Starfield Creation from Bethesda, given the user has legitimate access (free or purchased).

**Conclusion:** Technically possible but very difficult, and it violates Bethesda's TOS. No existing open-source tool does this for Starfield.

---

## How Creations Are Delivered

- The in-game Creations menu downloads files through Bethesda's **CDP (Content Delivery Platform)**
- Files land in `Data/` as standard `.esm`/`.esp`/`.esl` + `.ba2` — identical to regular mods
- `ContentCatalog.txt` (in `%LOCALAPPDATA%\Starfield\`) tracks installed Creations
- Files on Bethesda's CDN are **AES-encrypted** and zlib-compressed in chunks

## The Download Pipeline (reverse-engineered from older games)

1. Authenticate via `POST /session/login/` with Bethesda.net credentials -> session token
2. Subscribe to the mod via API
3. Get `cdp_product_id` / `cdp_branch_id` from content endpoint
4. Fetch file tree via CDP API
5. Get AES decryption keys (`ex_info_A`, `ex_info_B`)
6. Download encrypted chunks from CDN
7. Decrypt (AES-CTR) + decompress (zlib)

## Public vs. Gated Access

| What | Auth required? |
|------|---------------|
| Metadata (title, version, size, categories) | No — just public `x-bnet-key` from CDN config |
| Actual mod file downloads | Yes — Bethesda.net session + entitlement check + AES decryption |

The starfield-tool codebase already uses the public metadata API successfully (`api.bethesda.net/ugcmods/v2`).

### API Details

- **Public metadata API:** `https://api.bethesda.net/ugcmods/v2/content/{uuid}` and `https://api.bethesda.net/ugcmods/v2/content` (search)
- **Public API key source:** `https://cdn.bethesda.net/data/core` (the `ugc.bnetKey` field)
- **Auth header:** `x-bnet-key` (no user auth needed for metadata)
- The `download` array in the API response contains per-platform `published` entries with file sizes, but **not** the actual download URLs

## Existing Tools & Projects

| Project | What it does | Starfield support |
|---------|-------------|-------------------|
| [Nukem9/bethnet-cli](https://github.com/Nukem9/bethnet-cli) | C# CLI that can authenticate, subscribe, and download+decrypt Bethesda mods | Fallout 4 era; Starfield untested/unlikely |
| [osvein/BethNetWrapper](https://github.com/osvein/BethNetWrapper) | Reverse-engineered API notes for old bethesda.net REST API | Pre-Starfield, likely outdated |
| [hst12/Starfield-Creations-Mod-Manager](https://github.com/hst12/Starfield-Tools---ContentCatalog.txt-fixer) | Manages ContentCatalog.txt, load order, backup/restore; does NOT download | Yes, but offline only |

**No existing open-source tool successfully downloads Starfield Creations programmatically.**

The `bethnet-cli` tool works with the older API (`mods.services.bethesda.net`) and uses Bethesda.net username/password auth + AES decryption of CDP content, but has not been updated for Starfield's newer API (`api.bethesda.net/ugcmods/v2`).

## Starfield's Mod System: Creations vs Regular Mods

- **On disk, they are identical**: both are `.esm`/`.esp`/`.esl` + `.ba2` files in the `Data/` directory
- **The difference is management**: Creations are tracked in `ContentCatalog.txt` (JSON), managed by the in-game Creations menu, and downloaded through Bethesda's servers. Regular mods are manually installed or managed by Vortex/MO2.
- `ContentCatalog.txt` serves as the manifest/catalog of installed Creations
- Having an `.esm` in the load order automatically loads matching `.ba2` archives (e.g., `MyMod - Main.ba2`)

## Authentication

- **Metadata queries**: No user auth needed. Just the public `x-bnet-key` from the CDN config.
- **Downloads**: Require a **Bethesda.net account** authenticated via their session API. Login endpoint takes username/password and returns a session token (~5 min validity, refreshable).
- **Account linking**: Bethesda.net accounts can be linked to Xbox/Microsoft and Steam accounts, but API auth uses Bethesda.net credentials directly.
- **For Starfield's newer Creations system**: It is unclear whether the old `bethnet-cli` auth flow still works. The CDP may still be the backend, but the auth flow may have changed.

## Legal / TOS Considerations

From the [ZeniMax Media Terms of Service](https://www.zenimax.com/en/legal/terms-of-service):

- **Reverse engineering prohibited**: "You may not modify, adapt, reverse engineer or decompile the Software, or otherwise attempt to derive source code."
- **Bots/automation prohibited**: "You may not use cheats, automation software (bots), hacks, mods or any other unauthorized third-party software designed to modify the Application."
- **Content downloading restricted**: "You may not copy, use or download any Content from a Service unless you are expressly authorized to do so by ZeniMax in writing."
- **Access restricted**: "You may not otherwise access, receive, play or use any Services except as expressly provided in these Terms of Service."

These clauses **clearly prohibit** programmatic downloading of Creations content without explicit authorization. Querying the public metadata API (as our codebase already does) is a grayer area since that data is served publicly without authentication, but downloading actual mod files programmatically would violate the TOS.

## Practical Recommendation

The viable path remains: **users download Creations via the in-game menu**, and starfield-tool manages them afterward via `ContentCatalog.txt` and `Plugins.txt`. Building a downloader would require:

1. Reverse-engineering the newer CDP auth flow for Starfield's API
2. Handling AES-CTR decryption of file chunks
3. Managing entitlement/subscription checks
4. Violating Bethesda's TOS

This is **not recommended** for implementation.

## References

- [Nukem9/bethnet-cli](https://github.com/Nukem9/bethnet-cli) — C# Bethesda API client with download capability (older games)
- [osvein/BethNetWrapper](https://github.com/osvein/BethNetWrapper) — Reverse-engineered API notes
- [hst12/Starfield-Creations-Mod-Manager](https://github.com/hst12/Starfield-Tools---ContentCatalog.txt-fixer) — ContentCatalog.txt manager
- [Starfield Creations Mod Manager on Nexus](https://www.nexusmods.com/starfield/mods/10432)
- [ZeniMax Terms of Service](https://www.zenimax.com/en/legal/terms-of-service)
- [Bethesda Modding Guidelines](https://help.bethesda.net/app/answers/detail/a_id/51731)
- [Starfield Modding Guide (GitHub)](https://github.com/ejams1/starfield-modding-guide)
- [Starfield Creations Portal](https://creations.bethesda.net/en/starfield/all)
