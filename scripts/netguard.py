"""Polite, honest network behaviour (rules: rulebooks/15-security.md). Goal: never get banned, never look like abuse.
- Per-host minimum gap + jitter + daily maximum (ledger kept in Drive `jobs/state/_net.json`, shared by every worker run).
- Tripwire: a block signal (429, 403, challenge, captcha, login wall ...) puts that host in COOLDOWN (growing: hours -> days) and
  raises HostBlocked. We never retry harder, never change identity, never use proxies, never solve challenges. A human decides.
- safe_download: https only, public addresses only (no SSRF), size cap, content sniffing, no executables, HTML-instead-of-media = block page.
Identity is always the plain, honest user agent from config/network.json."""
import ipaddress
import json
import random
import re
import socket
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .common import ROOT, load_json

NET_STATE = "jobs/state/_net.json"
CFG_PATH = ROOT / "config" / "network.json"


class HostBlocked(RuntimeError):
    """The host said stop (or we are in cooldown / over the daily maximum). Do not retry; alert the human."""


def config():
    return load_json(CFG_PATH)


def _day(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")


def host_key(url_or_host, cfg=None):
    cfg = cfg or config()
    host = (re.sub(r"^\w+://", "", url_or_host).split("/")[0].split(":")[0]).lower()
    for key, h in cfg["hosts"].items():
        if any(host == m or host.endswith("." + m) for m in h.get("match", [])):
            return key
    return "default"


def block_reason(status=None, text="", cfg=None):
    """Return why this answer means 'stop', or None. Looks at the HTTP status and the tail of the message/body."""
    cfg = cfg or config()
    if status in (401, 403, 429, 503):
        return f"HTTP {status}"
    t = (text or "")[-4000:]
    for pat in cfg["block_signals"]:
        if re.search(pat, t, re.I):
            return f"signal '{pat}'"
    return None


class NetGuard:
    def __init__(self, cfg=None, ledger=None, clock=time.time, sleep=time.sleep, rng=random.random, persist=None):
        self.cfg = cfg or config()
        self.ledger = ledger if ledger is not None else {}
        self.clock, self.sleep, self.rng, self.persist = clock, sleep, rng, persist

    # ---- persistence (Drive state file); failures here never break work
    def attach(self, storage):
        try:
            self.ledger = storage.read_json(NET_STATE) if storage.exists(NET_STATE) else {}
        except Exception:  # noqa: BLE001
            self.ledger = {}
        self.persist = lambda led: storage.write_state(NET_STATE, led)

    def _save(self):
        if self.persist:
            try:
                self.persist(self.ledger)
            except Exception:  # noqa: BLE001
                pass

    def _row(self, key):
        now = self.clock()
        r = self.ledger.setdefault(key, {"day": _day(now), "count": 0, "last_ts": 0.0, "strikes": 0, "blocked_until": 0.0})
        if r["day"] != _day(now):
            r["day"], r["count"] = _day(now), 0
        if r.get("strikes") and now - r.get("last_block_ts", 0) > 7 * 86400:
            r["strikes"] = 0                       # a quiet week forgives
        return r

    # ---- the two calls around every request
    def before(self, key):
        h = self.cfg["hosts"].get(key) or self.cfg["hosts"]["default"]
        r = self._row(key)
        now = self.clock()
        if r["blocked_until"] > now:
            raise HostBlocked(f"{key} is in cooldown until {datetime.fromtimestamp(r['blocked_until'], timezone.utc):%Y-%m-%d %H:%M} UTC ({r.get('reason')})")
        if r["count"] >= h["daily_max"]:
            raise HostBlocked(f"{key}: daily maximum {h['daily_max']} reached; continues after 00:00 UTC")
        gap = h["min_gap_s"] + self.rng() * h.get("jitter_s", 0)
        wait = r["last_ts"] + gap - now
        if wait > 0:
            self.sleep(min(wait, 600))
        r["count"] += 1
        r["last_ts"] = self.clock()
        self._save()

    def after(self, key, status=None, text=""):
        why = block_reason(status, text, self.cfg)
        if not why:
            return
        h = self.cfg["hosts"].get(key) or self.cfg["hosts"]["default"]
        r = self._row(key)
        r["strikes"] = r.get("strikes", 0) + 1
        hours = h["cooldown_h"][min(r["strikes"], len(h["cooldown_h"])) - 1]
        r["blocked_until"] = self.clock() + hours * 3600
        r["last_block_ts"] = self.clock()
        r["reason"] = why
        self._save()
        raise HostBlocked(f"{key} said stop ({why}). Paused {hours} h. No workaround is tried.")

    def call(self, key, fn):
        """fn() does one request. Errors that look like a block start the cooldown."""
        self.before(key)
        try:
            out = fn()
        except HostBlocked:
            raise
        except urllib.error.HTTPError as e:
            self.after(key, e.code, str(e))
            raise
        except Exception as e:  # noqa: BLE001
            self.after(key, None, str(e))
            raise
        return out

    def status(self):
        now = self.clock()
        return {k: {"today": v.get("count", 0), "strikes": v.get("strikes", 0),
                    "blocked": v.get("blocked_until", 0) > now, "reason": v.get("reason")} for k, v in self.ledger.items()}


_G = None


def guard():
    global _G
    if _G is None:
        _G = NetGuard()
    return _G


# ------------------------------------------------------------------ safe download
MAGIC = [
    (b"ID3", "audio"), (b"\xff\xfb", "audio"), (b"\xff\xf3", "audio"), (b"\xff\xf2", "audio"), (b"\xff\xf1", "audio"), (b"\xff\xf9", "audio"),
    (b"OggS", "audio"), (b"fLaC", "audio"), (b"\x89PNG\r\n\x1a\n", "image"), (b"\xff\xd8\xff", "image"), (b"GIF8", "image"),
    (b"wOFF", "font"), (b"wOF2", "font"), (b"\x00\x01\x00\x00", "font"), (b"OTTO", "font"), (b"%PDF-", "pdf"), (b"\x1a\x45\xdf\xa3", "video"),
]
DANGER = [(b"MZ", "Windows program"), (b"\x7fELF", "Linux program"), (b"#!", "script"), (b"PK\x03\x04", "zip archive"),
          (b"\x1f\x8b", "gzip archive"), (b"<?php", "php script"), (b"Rar!", "rar archive"), (b"7z\xbc\xaf", "7z archive")]


def sniff(head):
    """-> (kind | 'html' | 'text' | 'unknown', danger_or_None). Looks at the first bytes only."""
    for sig, what in DANGER:
        if head.startswith(sig):
            return "danger", what
    low = head[:200].lstrip().lower()
    if low.startswith((b"<!doctype", b"<html", b"<head", b"<body")):
        return "html", None
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio", None
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image", None
    if head[4:8] == b"ftyp":
        return ("audio" if head[8:12] in (b"M4A ", b"M4B ") else "video"), None
    for sig, kind in MAGIC:
        if head.startswith(sig):
            return kind, None
    return "unknown", None


def is_public_host(host, resolver=None):
    """False if the name points at a private / loopback / link-local / metadata address (SSRF protection)."""
    try:
        infos = (resolver or (lambda h: [i[4][0] for i in socket.getaddrinfo(h, None)]))(host)
    except Exception:  # noqa: BLE001
        return False
    return bool(infos) and all(ipaddress.ip_address(a).is_global for a in infos)


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, resolver, limit):
        self.resolver, self.limit, self.n = resolver, limit, 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.n += 1
        if self.n > self.limit:
            raise urllib.error.URLError("too many redirects")
        if not newurl.lower().startswith("https://"):
            raise urllib.error.URLError("redirect to a non-https address refused")
        host = newurl.split("/")[2].split(":")[0]
        if not is_public_host(host, self.resolver):
            raise urllib.error.URLError("redirect to a private address refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_download(url, dest, kind, only_hosts=None, guard_=None, resolver=None, opener=None, cfg=None):
    """Download one file the careful way. kind in config.download.max_mb. Returns dest. Raises ValueError (rejected file) or
    HostBlocked. A rejected file never stays on disk."""
    cfg = cfg or config()
    g = guard_ or guard()
    if not url.lower().startswith("https://"):
        raise ValueError("only https downloads are allowed")
    host = url.split("/")[2].split(":")[0].lower()
    if only_hosts and not any(host == h or host.endswith("." + h) for h in only_hosts):
        raise ValueError(f"host {host} is not on the allowed list for this download")
    if not is_public_host(host, resolver):
        raise ValueError(f"{host} does not resolve to a public address")
    key = host_key(host, cfg)
    cap = int(cfg["download"]["max_mb"][kind]) * 1024 * 1024
    dest = Path(dest)
    part = dest.with_name(dest.name + ".part")

    def go():
        req = urllib.request.Request(url, headers={"User-Agent": cfg["user_agent"]})
        op = opener or urllib.request.build_opener(_SafeRedirect(resolver, cfg["download"]["redirects_max"]))
        with op.open(req, timeout=cfg["download"]["timeout_s"]) as r:
            ln = r.headers.get("Content-Length")
            if ln and int(ln) > cap:
                raise ValueError(f"file is {int(ln) // 1048576} MB, limit for {kind} is {cap // 1048576} MB")
            size = 0
            with open(part, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > cap:
                        raise ValueError(f"download passed the {cap // 1048576} MB limit for {kind}")
                    f.write(chunk)
    try:
        g.call(key, go)
        with open(part, "rb") as f:
            head = f.read(512)
        got, danger = sniff(head)
        if danger:
            raise ValueError(f"refused: file is a {danger}")
        if got == "html":
            g.after(key, 403, "Just a moment")      # a web page instead of a file = block / login page
        if kind != "model" and got != kind and not (kind == "video" and got == "audio"):
            raise ValueError(f"expected {kind}, the file looks like {got}")
        part.replace(dest)
        return dest
    finally:
        if part.exists():
            part.write_bytes(b"")                   # no delete calls in our code: empty the leftover and let the temp area go
