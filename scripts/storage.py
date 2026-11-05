"""Drive storage layer.

Two modes:
  1. Mounted/local root  (ITCOD_DRIVE_ROOT): Colab mount, Drive for Desktop, or a local test folder.
  2. rclone remote       (ITCOD_RCLONE_REMOTE, e.g. "gdrive:ITCODLAB-VIDEO"): uses `rclone copyto` only.

Rules enforced here:
  - There is no delete function.
  - Files are never overwritten: an existing name gets a _v2, _v3 ... suffix.
  - Only files under jobs/state/ may be updated in place (job status files).
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .common import limits

STATE_PREFIXES = tuple(limits()["storage"]["overwrite_allowed_only_under"])


class StorageError(RuntimeError):
    pass


def _versioned_name(name, exists):
    """name.ext -> name_v2.ext, name_v3.ext ... until exists(candidate) is False."""
    p = Path(name)
    stem, suffix = p.stem, p.suffix
    n = 2
    while True:
        cand = str(p.with_name(f"{stem}_v{n}{suffix}"))
        if not exists(cand):
            return cand
        n += 1


class Storage:
    def __init__(self, root=None, remote=None):
        root = root or os.environ.get("ITCOD_DRIVE_ROOT")
        self.root = Path(root) if root else None
        self.remote = remote or os.environ.get("ITCOD_RCLONE_REMOTE")
        if self.root is None and not self.remote:
            raise StorageError(
                "No storage configured. Set ITCOD_DRIVE_ROOT (mounted Drive folder) "
                "or ITCOD_RCLONE_REMOTE (rclone remote path)."
            )
        if self.root is not None:
            self.root.mkdir(parents=True, exist_ok=True)

    # ---------- read side ----------
    def exists(self, rel):
        if self.root is not None:
            return (self.root / rel).exists()
        rc = subprocess.run(["rclone", "lsf", f"{self.remote}/{rel}"], capture_output=True, text=True)
        return rc.returncode == 0 and rc.stdout.strip() != ""

    def list_dir(self, rel):
        if self.root is not None:
            d = self.root / rel
            return sorted(p.name for p in d.iterdir()) if d.is_dir() else []
        r = subprocess.run(["rclone", "lsf", f"{self.remote}/{rel}"], capture_output=True, text=True)
        if r.returncode != 0:
            return []
        return sorted(x.rstrip("/") for x in r.stdout.splitlines() if x.strip())

    def read_text(self, rel):
        if self.root is not None:
            return (self.root / rel).read_text(encoding="utf-8")
        r = subprocess.run(["rclone", "cat", f"{self.remote}/{rel}"], capture_output=True, text=True)
        if r.returncode != 0:
            raise StorageError(f"cannot read {rel}: {r.stderr[-300:]}")
        return r.stdout

    def read_json(self, rel):
        return json.loads(self.read_text(rel))

    def fetch(self, rel, local_path):
        """Copy a Drive file to a local path (the local path may be overwritten: it is scratch)."""
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if self.root is not None:
            shutil.copyfile(self.root / rel, local_path)
        else:
            r = subprocess.run(["rclone", "copyto", f"{self.remote}/{rel}", str(local_path)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise StorageError(f"cannot fetch {rel}: {r.stderr[-300:]}")
        return local_path

    # ---------- write side (never deletes, never overwrites) ----------
    def put_file(self, local_path, rel, versioned=True):
        local_path = Path(local_path)
        if not local_path.exists():
            raise StorageError(f"local file missing: {local_path}")
        if versioned and self.exists(rel):
            rel = _versioned_name(rel, self.exists)
        elif not versioned and not rel.startswith(STATE_PREFIXES):
            raise StorageError(f"in-place update not allowed outside {STATE_PREFIXES}: {rel}")
        if self.root is not None:
            dest = self.root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(local_path, dest)
        else:
            r = subprocess.run(["rclone", "copyto", str(local_path), f"{self.remote}/{rel}"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise StorageError(f"upload failed for {rel}: {r.stderr[-300:]}")
        return rel

    def ensure_dir(self, rel):
        """Create an (empty) folder so it is visible in Drive. Never touches existing content."""
        if self.root is not None:
            (self.root / rel).mkdir(parents=True, exist_ok=True)
        else:
            subprocess.run(["rclone", "mkdir", f"{self.remote}/{rel}"], capture_output=True, text=True)

    def put_text(self, rel, text, versioned=True):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".tmp", encoding="utf-8") as t:
            t.write(text)
            tmp = t.name
        return self.put_file(tmp, rel, versioned=versioned)

    def put_json(self, rel, obj, versioned=True):
        return self.put_text(rel, json.dumps(obj, ensure_ascii=False, indent=2), versioned=versioned)

    def write_state(self, rel, obj):
        """Job status files only. Updated in place (Drive keeps revision history)."""
        if not rel.startswith(STATE_PREFIXES):
            raise StorageError(f"write_state only under {STATE_PREFIXES}: {rel}")
        return self.put_text(rel, json.dumps(obj, ensure_ascii=False, indent=2), versioned=False)

    def put_tree(self, local_dir, rel_dir):
        """Copy every file of a local folder to Drive. Existing names are kept, new ones get _vN."""
        local_dir = Path(local_dir)
        out = []
        for p in sorted(local_dir.rglob("*")):
            if p.is_file():
                out.append(self.put_file(p, f"{rel_dir}/{p.relative_to(local_dir).as_posix()}"))
        return out

    def copy_within(self, src_rel, dst_rel):
        """Copy inside Drive (used to publish an approved final). Never overwrites."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / Path(src_rel).name
            self.fetch(src_rel, tmp)
            return self.put_file(tmp, dst_rel)
