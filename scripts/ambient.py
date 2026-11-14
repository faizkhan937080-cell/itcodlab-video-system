"""Own dark-ambient bed (free, no licence, no network): low drone + slow-moving noise, made with ffmpeg only.
Used when the music library has no usable track, so a run never stops for a missing bed."""
import subprocess


def make(out_path, seconds=60):
    flt = (f"sine=f=55:d={seconds}[a];sine=f=82.4:d={seconds}[b];sine=f=110.7:d={seconds}[c];"
           f"anoisesrc=d={seconds}:c=brown:a=0.35[n];"
           "[a]volume=0.5[a1];[b]volume=0.3,tremolo=f=0.2:d=0.6[b1];[c]volume=0.12,tremolo=f=0.1:d=0.8[c1];"
           "[n]lowpass=f=420[n1];[a1][b1][c1][n1]amix=inputs=4:normalize=0,lowpass=f=900,"
           f"afade=t=in:d=2,afade=t=out:st={seconds - 3}:d=3[o]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", flt, "-map", "[o]", "-ac", "2",
                    "-ar", "44100", "-b:a", "160k", str(out_path)], check=True, timeout=120)
    return str(out_path)
