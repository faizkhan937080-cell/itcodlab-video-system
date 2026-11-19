"""Own sound effects for meme beats (free, no licence, no network): made with ffmpeg only, added to the library by name.
These are original recreations of the common meme sounds (impact boom, buzzer, record scratch, whoosh, siren, ding, pop), not the copyrighted clips."""
import subprocess

RECIPES = {
    # low sine that drops in pitch + noise burst = the "meme boom" hit
    "boom": "sine=f=70:d=0.9[a];anoisesrc=d=0.9:c=pink:a=0.5[n];[a]volume=1.4,afade=t=out:st=0.05:d=0.85[a1];[n]lowpass=f=600,afade=t=out:st=0:d=0.35[n1];[a1][n1]amix=inputs=2:normalize=0,acompressor=threshold=0.2:ratio=6[o]",
    "buzzer": "sine=f=110:d=0.7[a];sine=f=117:d=0.7[b];[a][b]amix=inputs=2:normalize=0,volume=1.6,tremolo=f=30:d=0.9,afade=t=out:st=0.5:d=0.2[o]",
    "scratch": "anoisesrc=d=0.55:c=white:a=0.6[n];[n]highpass=f=900,lowpass=f=5200,tremolo=f=18:d=0.9,afade=t=in:d=0.03,afade=t=out:st=0.35:d=0.2[o]",
    "whoosh": "anoisesrc=d=0.6:c=pink:a=0.8[n];[n]bandpass=f=1400:width_type=h:w=1800,afade=t=in:d=0.25,afade=t=out:st=0.3:d=0.3[o]",
    "siren": "sine=f=720:d=1.6[a];[a]vibrato=f=2.2:d=1,volume=0.5,afade=t=out:st=1.2:d=0.4[o]",
    "ding": "sine=f=1318:d=0.8[a];sine=f=1976:d=0.8[b];[a][b]amix=inputs=2:normalize=0,volume=0.8,afade=t=out:st=0.05:d=0.75[o]",
    "pop": "sine=f=520:d=0.12[a];[a]volume=1.2,afade=t=out:st=0.02:d=0.1[o]",
}


def make(name, out_path):
    flt = RECIPES[name]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", flt, "-map", "[o]", "-ac", "2", "-ar", "44100", str(out_path)], check=True, timeout=60)
    return str(out_path)
