"""One reel = one permanent ID = its Instagram shortcode. Same reel sent again (other link params, retry) never makes a second folder."""
import re

from . import layout

_RE = re.compile(r"instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:reel|reels|p|tv)/([A-Za-z0-9_-]{5,20})", re.I)
TERMINAL_BAD = ("FAILED", "NEEDS_INPUT")


def shortcode(link):
    m = _RE.search(link or "")
    return m.group(1) if m else ""


def canonical(link):
    c = shortcode(link)
    return f"https://www.instagram.com/reel/{c}/" if c else (link or "").strip()


def find_reel(storage, code):
    """Where is this reel's folder already? Looks in every creator folder, _unassigned and general."""
    if not code:
        return ""
    cands = [f"analysis/general/{code}"]
    for h in storage.list_dir("creators"):
        cands += [layout.reel_rel(h, code), f"creators/{h}/videos/{code}"]
    for rel in cands:
        if storage.exists(rel):
            return rel
    return ""


def new_job_id(storage, code):
    """reel-<code> the first time; after a FAILED/NEEDS_INPUT run reel-<code>-r2, -r3 ... Raises if the reel is already
    analysed or a job for it is still running (no duplicate folders)."""
    base = f"reel-{code}"
    n, jid = 1, base
    while storage.exists(f"jobs/state/{jid}.json") or storage.exists(f"jobs/inbox/{jid}.json"):
        if not storage.exists(f"jobs/state/{jid}.json"):
            raise ValueError(f"{jid} is already queued")
        st = storage.read_json(f"jobs/state/{jid}.json")
        if st.get("status") not in TERMINAL_BAD:
            raise ValueError(f"{jid} already exists ({st.get('status')}); no second job for the same reel")
        n += 1
        jid = f"{base}-r{n}"
    return jid
