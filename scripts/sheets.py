"""Optional Google Sheet mirror (status, approvals, DNA index).
Uses gspread with Google default credentials:
  - Colab: run `from google.colab import auth; auth.authenticate_user()` first (your own login, no key file).
  - VM: the attached service account.
If anything is missing the client simply stays disabled; the pipeline still works from Drive files.
"""
from .common import drive_cfg, log, now_iso

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]


class SheetsClient:
    def __init__(self):
        self.enabled = False
        self.error = None
        self.cfg = drive_cfg()["sheet"]
        try:
            import google.auth
            import gspread
            creds, _ = google.auth.default(scopes=SCOPES)
            self.gc = gspread.authorize(creds)
            self.sh = self.gc.open_by_key(self.cfg["id"])
            self.enabled = True
            self._ensure_headers()
        except Exception as e:  # noqa: BLE001
            self.error = str(e)[:200]
            log(f"sheet mirror disabled: {self.error}")

    def _ws(self, name):
        return self.sh.worksheet(name)

    def _ensure_headers(self):
        """Write headers only into tabs whose first row is empty. Never touches existing cells."""
        mapping = {"Jobs": "jobs_columns", "DNA_Index": "dna_index_columns",
                   "Creators": "creators_columns", "Approvals": "approvals_columns"}
        for tab, key in mapping.items():
            try:
                ws = self._ws(tab)
                if not any(c.strip() for c in ws.row_values(1)):
                    ws.update(range_name="A1", values=[self.cfg[key]])
            except Exception as e:  # noqa: BLE001
                log(f"sheet header check failed for {tab}: {str(e)[:120]}")

    def upsert_job(self, st, job):
        if not self.enabled:
            return
        try:
            ws = self._ws("Jobs")
            row = [st["id"], job.get("link") or job.get("file", ""), job.get("mode", ""), job.get("target", ""),
                   st["status"], st.get("output_link", ""), (st.get("note") or st.get("error_tail") or "")[:300]]
            ids = ws.col_values(1)
            if st["id"] in ids:
                r = ids.index(st["id"]) + 1
                ws.update(range_name=f"A{r}:G{r}", values=[row])
            else:
                ws.append_row(row, value_input_option="USER_ENTERED")
        except Exception as e:  # noqa: BLE001
            log(f"sheet job update failed: {str(e)[:120]}")

    def find_approval(self, job_id, gate, rev):
        """Return (decision, feedback) from the Approvals tab or (None, '')."""
        if not self.enabled:
            return None, ""
        try:
            for r in self._ws("Approvals").get_all_records():
                if (str(r.get("Job ID")) == job_id and str(r.get("Gate")) == str(gate)
                        and str(r.get("Rev") or 1) == str(rev) and str(r.get("Decision", "")).strip()):
                    return str(r["Decision"]).strip().upper()[:1], str(r.get("Feedback", ""))
        except Exception as e:  # noqa: BLE001
            log(f"sheet approval read failed: {str(e)[:120]}")
        return None, ""

    def log_approval(self, job_id, gate, rev, decision, feedback):
        if self.enabled:
            try:
                self._ws("Approvals").append_row([job_id, gate, rev, decision, feedback, now_iso()])
            except Exception as e:  # noqa: BLE001
                log(f"sheet approval log failed: {str(e)[:120]}")

    def add_dna_index(self, dna_id, scope, creator, dna_type, version, path, job_id):
        if self.enabled:
            try:
                self._ws("DNA_Index").append_row([dna_id, scope, creator, dna_type, version, path, job_id, now_iso()])
            except Exception as e:  # noqa: BLE001
                log(f"sheet dna index failed: {str(e)[:120]}")
