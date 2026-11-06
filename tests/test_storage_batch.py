import os
import stat
import sys
import textwrap
from pathlib import Path

from scripts.storage import Storage

FAKE = textwrap.dedent('''\
    #!{py}
    import json, os, shutil, sys
    from pathlib import Path
    log = Path(os.environ["FAKE_LOG"]); store = Path(os.environ["FAKE_STORE"])
    a = sys.argv[1:]
    with log.open("a") as f: f.write(a[0] + "\\n")
    def loc(x): return store / x.split(":", 1)[1]
    if a[0] == "lsf":
        d = loc(a[-1])
        if not d.exists(): sys.exit(3)
        if "-R" in a:
            print("\\n".join(str(p.relative_to(d)) for p in sorted(d.rglob("*")) if p.is_file()))
        else:
            print("\\n".join(p.name for p in sorted(d.iterdir())) if d.is_dir() else d.name)
    elif a[0] == "copy":
        if os.environ.get("FAKE_FAIL_COPY"): sys.exit(1)
        src, dst = Path(a[1]), loc(a[2])
        names = Path(a[a.index("--files-from") + 1]).read_text().split()
        for n in names:
            if not (dst / n).exists():
                (dst / n).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src / n, dst / n)
    elif a[0] == "copyto":
        src, dst = Path(a[1]), loc(a[2]); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
''')


def setup(tmp_path, monkeypatch, fail=False):
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    exe = bin_dir / "rclone"
    exe.write_text(FAKE.format(py=sys.executable))
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "calls.log"))
    monkeypatch.setenv("FAKE_STORE", str(tmp_path / "drive"))
    monkeypatch.delenv("ITCOD_DRIVE_ROOT", raising=False)
    if fail:
        monkeypatch.setenv("FAKE_FAIL_COPY", "1")
    (tmp_path / "drive").mkdir()
    src = tmp_path / "src"
    for i in range(6):
        (src / "sub").mkdir(parents=True, exist_ok=True)
        (src / ("a%d.txt" % i if i < 3 else "sub/b%d.txt" % i)).write_text("x%d" % i)
    return Storage(remote="fake:root"), src


def calls(tmp_path):
    return (tmp_path / "calls.log").read_text().split()


def test_put_tree_uses_one_listing_and_one_copy(tmp_path, monkeypatch):
    st, src = setup(tmp_path, monkeypatch)
    out = st.put_tree(src, "analysis/job1")
    assert sorted(out) == sorted(f"analysis/job1/{p.relative_to(src).as_posix()}" for p in src.rglob("*") if p.is_file())
    assert calls(tmp_path) == ["lsf", "copy"]
    assert (tmp_path / "drive/root/analysis/job1/sub/b3.txt").read_text() == "x3"


def test_existing_names_get_versioned_not_overwritten(tmp_path, monkeypatch):
    st, src = setup(tmp_path, monkeypatch)
    st.put_tree(src, "j")
    (src / "a0.txt").write_text("changed")
    st.put_tree(src, "j")
    base = tmp_path / "drive/root/j"
    assert (base / "a0.txt").read_text() == "x0" and (base / "a0_v2.txt").read_text() == "changed"


def test_failed_batch_copy_falls_back_without_duplicates(tmp_path, monkeypatch):
    st, src = setup(tmp_path, monkeypatch, fail=True)
    out = st.put_tree(src, "j")
    assert len(out) == 6
    names = sorted(p.name for p in (tmp_path / "drive/root/j").rglob("*") if p.is_file())
    assert names == ["a0.txt", "a1.txt", "a2.txt", "b3.txt", "b4.txt", "b5.txt"]
