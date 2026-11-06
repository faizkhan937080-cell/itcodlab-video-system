# toolbook: problems that come back (symptom -> fix recipe). Add a line when a problem is seen a 2nd time.
Format: T: symptom | FIX: recipe | seen: N (bump N each time). One-off mistakes stay in lessons/core.md.

T: Colab drive.mount MessageError / Saving failed | FIX: one tab only, force_remount cell, click Allow in popup, allow popups | seen: 3
T: Colab Gemini says "I will run" but nothing runs | FIX: click Accept and run (or Run all) | seen: 3
T: "Notebook does not have secret access" popup | FIX: Cancel; token is read from os.environ | seen: 3
T: Drive state file not updated yet | FIX: wait 60 s, read again; state file ids are stable | seen: 6
T: Drive connector image = base64 text | FIX: use review branch: ./run review-fetch <job> --out <dir>, then Read the jpg | seen: 2
T: Instagram/YouTube refuses cloud IP | FIX: use ITCOD_COOKIES or drop the file in Drive input/references/ | seen: 0 (IG worked once)
T: optional step (whisper, describe, review) crashes a job | FIX: wrap, return available:false/status failed, never raise | seen: 2
T: faster-whisper PyAV decode error on Python 3.13 | FIX: pass librosa array, not file path | seen: 1
T: Remotion cannot download its browser | FIX: set ITCOD_BROWSER to installed Chromium | seen: 2
T: job id rejected | FIX: 3-60 chars [A-Za-z0-9_-] | seen: 1
T: failed job (3 attempts) after a code bug | FIX: fix, push, wait ~5 min for worker self-update, send NEW id (-b, -c) | seen: 1
T: worker did not take new code | FIX: git remote in Colab clone must hold a token; else restart the worker cell | seen: 0
T: rmtree/unlink in scripts | FIX: never; test_code_has_no_delete_calls fails. use fresh timestamped dirs | seen: 1
T: file over 60 lines | FIX: shard it (./run mem add rolls over by itself) | seen: 0
T: secret pasted in chat | FIX: never repeat or store; tell him to regenerate later | seen: 1
T: git fetch of a single branch leaves no origin/<branch> | FIX: fetch with explicit refspec +refs/heads/X:refs/remotes/origin/X | seen: 1
T: tests push/write to real remote or Drive | FIX: conftest autouse env ITCOD_NO_REVIEW; review/an1, an2 on branch review are old test junk, leave | seen: 1
T: faces purple/blue in generated images | FIX: PIL is RGB, cv2 is BGR; convert back before imwrite; tests test_collage_tile_keeps_real_colors | seen: 1
T: pack upload of ~60 files took ~25 min (per-file rclone lsf+copyto, shared Drive client) | FIX: Storage.put_tree = 1 lsf -R + 1 rclone copy --files-from; fallback per-file; tests/test_storage_batch.py | seen: 1
T: whisper loops one word 30x ("करेट") at end of Hindi pass, inflating coverage and repeated phrases | FIX: script_metrics.collapse_loops in audio.transcribe pack; loop segments flagged, left out of text/coverage | seen: 1
