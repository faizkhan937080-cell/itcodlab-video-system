"""Outside add-ons for Remotion (Faiz 2026-11-12: clones use OUTSIDE text animations, fonts and components, never
Claude's own templates). Source registries are open-source (licence checked) and copied into the repo ("vendored")
so every render uses the exact same code:

  remotion/src/ext/<source>/            component + lib files, imports rewritten to relative paths
  remotion/src/ext/<source>/LICENSE     the source's licence, kept
  remotion/src/ext/REGISTRY.json        {component: {source, url, licence, commit, files, sha256, deps}}
  remotion/src/ext/<source>/CATALOG.json  every component of the source (name, title, description) -> search
                                          without re-reading the registry (no token waste)

Fonts: only Google Fonts through @remotion/google-fonts (official Remotion package).
`./run addon catalog --src <clone>` | `addon search <word>` | `addon add <name...> --src <clone>` | `addon list`
"""
import hashlib
import json
import re
from pathlib import Path

from .common import ROOT

EXT = ROOT / "remotion" / "src" / "ext"
REG = EXT / "REGISTRY.json"
SOURCES = {
    "remocn": {"url": "https://github.com/Remocn/remocn", "licence": "MIT", "prefixes": ("components/remocn/", "lib/remocn/")},
}
NPM_OK = {"remotion", "@remotion/captions", "@remotion/google-fonts", "@remotion/transitions", "@remotion/paths",
          "@remotion/media-utils", "@remotion/layout-utils", "@remotion/shapes", "@remotion/noise", "@remotion/animation-utils"}


def load_registry():
    try:
        return json.loads(REG.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _artifact(src_dir, name):
    p = Path(src_dir) / "registry-artifacts" / f"{name}.json"
    if not p.exists():
        raise FileNotFoundError(f"{name}: not in {p.parent}")
    return json.loads(p.read_text(encoding="utf-8"))


def catalog(src_dir, source="remocn"):
    """CATALOG.json of every component (name, title, description, npm deps)."""
    out = []
    for p in sorted((Path(src_dir) / "registry-artifacts").glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        out.append({"name": d.get("name", p.stem), "title": d.get("title", ""), "description": d.get("description", ""),
                    "deps": d.get("dependencies", []), "type": d.get("type", "")})
    dest = EXT / source
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "CATALOG.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    return len(out)


def search(word, source="remocn"):
    try:
        cat = json.loads((EXT / source / "CATALOG.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    w = [x.lower() for x in word.split()]
    return [c for c in cat if all(x in (c["name"] + " " + c["title"] + " " + c["description"]).lower() for x in w)]


def _target_rel(target, source):
    for pre in SOURCES[source]["prefixes"]:
        if target.startswith(pre):
            return target[len(pre):]
    raise ValueError(f"unexpected target path {target}")


def _rewrite(content, here_rel, source):
    """'@/lib/remocn/x' and '@/components/remocn/x' -> relative imports inside ext/<source>/."""
    here_dir = Path(here_rel).parent

    def rel(m):
        target = m.group(2)
        rp = Path(target)
        r = Path(*([".."] * len(here_dir.parts))) / rp if here_dir.parts else rp
        s = str(r).replace("\\", "/")
        return f'{m.group(1)}{s if s.startswith(".") else "./" + s}{m.group(3)}'
    return re.sub(r'(from\s+["\'])@/(?:lib|components)/' + source + r'/([^"\']+)(["\'])', rel, content)


def add(names, src_dir, source="remocn", commit=""):
    """Copy components + their registry dependencies. Returns {added: [...], npm: [...], refused: [...]}"""
    meta = SOURCES[source]
    reg = load_registry()
    dest = EXT / source
    dest.mkdir(parents=True, exist_ok=True)
    lic = Path(src_dir) / "LICENSE"
    if lic.exists():
        (dest / "LICENSE").write_text(lic.read_text(encoding="utf-8"), encoding="utf-8")
    todo, seen, added, npm, refused = list(names), set(), [], set(), []
    while todo:
        n = todo.pop(0)
        if n in seen:
            continue
        seen.add(n)
        art = _artifact(src_dir, n)
        bad = [d for d in art.get("dependencies", []) if d not in NPM_OK and not d.startswith("@remotion/google-fonts")]
        if bad:
            refused.append({"name": n, "needs": bad})
            continue
        npm.update(art.get("dependencies", []))
        files, h = [], hashlib.sha256()
        for f in art.get("files", []):
            rel = _target_rel(f["target"], source)
            text = _rewrite(f["content"], rel, source)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            h.update(text.encode("utf-8"))
            files.append(f"ext/{source}/{rel}")
        reg[n] = {"source": source, "url": f"{meta['url']}/tree/main/registry/remocn/{n}", "licence": meta["licence"],
                  "commit": commit, "title": art.get("title", ""), "files": files, "sha256": h.hexdigest()[:16],
                  "deps": sorted(art.get("dependencies", []))}
        added.append(n)
        for dep in art.get("registryDependencies", []):
            todo.append(dep.split("/")[-1])
    REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    write_index()
    return {"added": added, "npm": sorted(npm), "refused": refused}


def _export_name(path):
    text = (ROOT / "remotion" / "src" / path).read_text(encoding="utf-8")
    m = re.search(r"export (?:function|const) ([A-Z][a-z][A-Za-z0-9]*)\b", text)
    return m.group(1) if m else None


def write_index():
    """remotion/src/ext/index.ts: name -> component for every registered add-on and replica (static imports, so the
    bundle is the same on every machine). Lib-only entries (no capitalised export) are skipped."""
    lines = ["// generated by scripts/addons.py write_index(): do not edit by hand", "import type React from 'react';"]
    names = []
    for i, (name, e) in enumerate(sorted(load_registry().items())):
        f = (e.get("files") or [None])[0]
        if not f or not f.endswith(".tsx") or not (ROOT / "remotion" / "src" / f).exists():
            continue
        exp = _export_name(f)
        if not exp:
            continue
        rel = "../" + f[:-4]
        rel = rel.replace("../ext/", "./")
        lines.append(f"import {{{exp} as C{i}}} from '{rel}';")
        names.append((name, f"C{i}"))
    lines.append("export const EXT: Record<string, React.FC<any>> = {")
    lines += [f"  '{n}': {c} as React.FC<any>," for n, c in names]
    lines.append("};")
    (EXT / "index.ts").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(names)


def write_fonts(names=None):
    """remotion/src/ext/fonts.ts: Google fonts (official @remotion/google-fonts) used by clones. Keeps the list in
    ext/FONTS.json so adding one font never drops another."""
    import json as _j
    fj = EXT / "FONTS.json"
    have = _j.loads(fj.read_text(encoding="utf-8")) if fj.exists() else []
    known = set(_j.loads((ROOT / "config" / "google_fonts.json").read_text(encoding="utf-8")))
    for n in names or []:
        if n not in known:
            raise ValueError(f"{n} is not a Google font module in @remotion/google-fonts")
        if n not in have:
            have.append(n)
    fj.write_text(_j.dumps(have), encoding="utf-8")
    lines = ["// generated by scripts/addons.py write_fonts(): do not edit by hand"]
    for i, n in enumerate(have):
        lines.append(f"import {{loadFont as f{i}}} from '@remotion/google-fonts/{n}';")
    lines.append("export const FONTS: Record<string, string> = {")
    lines += [f"  '{n}': f{i}().fontFamily," for i, n in enumerate(have)]
    lines.append("};")
    (EXT / "fonts.ts").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return have
