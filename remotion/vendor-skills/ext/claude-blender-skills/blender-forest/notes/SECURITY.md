# Security check of roe.num77 downloads (2026-10-19)

Source: the tutorial's free asset posts, unpacked to blender-forest\assets (one folder per archive, nothing run).

| Check | Result |
|---|---|
| Windows Defender custom scan (archives + unpacked folder), signatures updated 2026-10-19 | clean, no detections |
| Archive contents (7z listing): any .exe .dll .bat .cmd .ps1 .vbs .js .jar .msi .scr .lnk .py .sh | none in the 5 archives used |
| Unpacked files are only: .blend, .hdr, .jpg, .png, .tif, .txt | yes |
| Terrain.blend and Plant library .blend opened headless with --disable-autoexec: embedded text/script blocks | 0 |
| Scripted drivers / OSL script nodes in them | 0 |
| Linked external .blend libraries | 0 |

Car files (rigacar.rar, Porsche Carrera.rar, Porsche Gtr_Rigged.rar): checked later, see the addendum below. Only needed after the 17 s mark. Do NOT install the add-on (your own-code-only rule).

Rules kept: Blender always run with --disable-autoexec on his files; no add-ons from him installed.

Textures (post 379, textures.rar 1.4 GB): Defender clean; contents only 374 jpg, 27 png, 2 tif, 2 hdr. Unpacked to `Plant models\textures\`. Plant library now resolves 415 of 416 images; the 1 missing is a junk path `C:\Map #1781324284` (leftover from the creator's export).

## Addendum: car files (post 382-384), unpacked to blender-forest\quarantine (not installed)
- Defender scan of the download folder already covered them: clean.
- Porsche Carrera.blend and Porsche Gtr_Rigged.blend, opened headless --disable-autoexec: 0 text/script blocks, 0 scripted drivers, 0 OSL nodes, 0 linked libraries.
- rigacar-Jeanyan3D-Fix-v3.zip = Rig-A-Car add-on (open source by digicreatures, "Jeanyan3D fix" is a third-party patch). Source read: 4 .py files, only imports bpy, bpy_extras, math, mathutils, re, itertools, importlib. No network, subprocess, os, exec/eval, file writes. Only URLs are doc/issue links in metadata.
- Caveat: the zip also ships precompiled .pyc files (cannot be read). Do not install as-is; if we ever use it, delete the __pycache__ folder first. Not needed for 0-16 s anyway.
