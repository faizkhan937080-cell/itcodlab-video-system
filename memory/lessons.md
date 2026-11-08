# lessons
keys: lessons
- 2026-11-06 00:17Z 2026-11-06 reel -e FAILED on GitHub worker: yt-dlp left single streams (source.fdash-*.m4a); _acquire took files[0] (alphabetical) = audio-only -> 'cannot open video'. Fix: pick_source() takes the merged video only, errors with file list otherwise. Instagram download from GitHub IP itself WORKED.
- 2026-11-06 00:31Z 2026-11-06 reel -f NEEDS_INPUT: GitHub runner had no ffmpeg at download so yt-dlp left video-only + audio-only streams. Fix: apt installs ffmpeg in worker.yml AND merge_streams() joins them losslessly (-c copy). Whisper/ffprobe need ffmpeg too: always check 'ffmpeg -version' line of the Actions log.
