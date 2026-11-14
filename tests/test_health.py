from scripts import health


def test_health_reports_every_service_even_with_no_keys():
    res = health.checks(env={})
    names = {r["service"] for r in res}
    assert {"sarvam_tts", "google_tts", "gemini_key", "huggingface_token", "kaggle_api", "modal"} <= names
    assert all(r["ok"] is False for r in res)   # nothing set = nothing trusted
