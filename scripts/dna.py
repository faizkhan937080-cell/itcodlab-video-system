"""Schema validation and versioned DNA saving. Nothing is overwritten or deleted."""
import json
import re

from jsonschema import Draft7Validator

from .common import ROOT, now_iso, tail

SCHEMAS = {
    "editing": "dna-editing.schema.json", "scripting": "dna-scripting.schema.json",
    "sound": "dna-sound.schema.json", "corpus": "dna-corpus.schema.json", "scene": "scene.schema.json", "job": "job.schema.json",
}
REQUIRED_TYPES = {"video": ["editing"], "audio": ["sound", "scripting"], "both": ["editing", "scripting", "sound"]}


def load_schema(name):
    with open(ROOT / "schemas" / SCHEMAS[name], "r", encoding="utf-8") as f:
        return json.load(f)


def validate(name, obj):
    """Return a list of error strings (empty list = valid)."""
    v = Draft7Validator(load_schema(name))
    errs = []
    for e in sorted(v.iter_errors(obj), key=lambda e: list(e.absolute_path)):
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        errs.append(f"{path}: {e.message}")
    return errs


def errors_tail(errs):
    return tail("\n".join(errs))


def dna_dir(target, dna_type):
    """target = 'general' or 'creator:<name>'  ->  Drive folder for that DNA type."""
    if target == "general":
        return f"dna/general/{dna_type}"
    name = target.split(":", 1)[1]
    return f"dna/creators/{name}/{dna_type}"


def next_version(storage, folder):
    pat = re.compile(r"^dna-v(\d+)\.json$")
    nums = [int(m.group(1)) for n in storage.list_dir(folder) if (m := pat.match(n))]
    return (max(nums) + 1) if nums else 1


def save_dna(storage, target, dna_type, candidate, job_id):
    """Write dna-vN.json (N = next free number). Returns (rel_path, version)."""
    folder = dna_dir(target, dna_type)
    ver = next_version(storage, folder)
    obj = dict(candidate)
    obj["_meta"] = {"version": ver, "scope": target, "source_job": job_id,
                    "approved_gate": 3, "saved_at": now_iso()}
    rel = storage.put_json(f"{folder}/dna-v{ver}.json", obj)
    return rel, ver
