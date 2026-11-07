"""Expectation evaluator: after EVERY generation, compare the result with the reference DNA and decide the next step.

Ladder (rulebooks/21-evaluator.md): PASS -> plan fix (Remotion/plan/finish, max 2) -> LTX footage (free, max 2)
-> ASK Faiz for MiniMax H3 (paid GPU, only after his Y in chat) -> FAILED. State lives in a small JSON file per job.
Numbers come from dna_check.clone_report (same scripts that analysed the reference) and qa.run findings.
`footage_needs` = shots Claude judged NOT reproducible by code (seen in the collage vs the reference), e.g. realistic scenes.
"""
import json
from pathlib import Path

from .common import now_iso
from .dna_check import clone_report

PLAN_TRIES, LTX_TRIES, MINIMAX_TRIES = 2, 2, 1
ASK_MINIMAX = "MiniMax H3 use karun? LTX se ye shot theek nahi bana. Y/N"


def new_state():
    return {"attempt": {"plan": 0, "ltx": 0, "minimax": 0}, "minimax_approved": False, "log": []}


def load_state(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else new_state()


def save_state(path, state):
    Path(path).write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def approve_minimax(state):
    """Only the CLI `approve-engine` calls this, after Faiz's Y in chat."""
    state["minimax_approved"] = True
    return state


def evaluate(dna_type, target, output_summary, qa_findings=(), footage_needs=(), state=None):
    """Returns {verdict, step, differences, qa_fail, footage_needs, ask, state}. verdict: PASS | FIX | ASK | FAILED."""
    state = state or new_state()
    att = state["attempt"]
    diffs = clone_report(dna_type, target, output_summary)["differences"] if target is not None else []
    fails = [x for x in qa_findings if x.get("level") == "fail"]
    needs = [str(n) for n in footage_needs]
    out = {"differences": diffs, "qa_fail": fails, "footage_needs": needs, "ask": None, "step": None}
    if not diffs and not fails and not needs:
        out["verdict"] = "PASS"
    elif (diffs or fails) and att["plan"] < PLAN_TRIES:
        out["verdict"], out["step"] = "FIX", "plan"
        att["plan"] += 1
    elif needs and att["ltx"] < LTX_TRIES:
        out["verdict"], out["step"] = "FIX", "ltx"
        att["ltx"] += 1
    elif needs and state.get("minimax_approved") and att["minimax"] < MINIMAX_TRIES:
        out["verdict"], out["step"] = "FIX", "minimax"
        att["minimax"] += 1
    elif needs and not state.get("minimax_approved") and att["minimax"] < MINIMAX_TRIES:
        out["verdict"], out["ask"] = "ASK", ASK_MINIMAX
    else:
        out["verdict"] = "FAILED"   # retries used up: stop, tell Faiz in one line
    state["log"].append({"at": now_iso(), "verdict": out["verdict"], "step": out["step"],
                         "diffs": len(diffs), "qa_fail": len(fails), "needs": len(needs)})
    out["state"] = state
    return out
