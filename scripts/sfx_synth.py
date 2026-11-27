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
RECIPES.update({
    # soft UI pop: quick falling sine + tiny click, rounded (the reel's object / caption entry sound)
    "softpop": "aevalsrc='sin(2*PI*(900-1300*t)*t)*exp(-t*38)*0.9':d=0.18[a];[a]lowpass=f=2600,afade=t=in:d=0.004[o]",
    "swish": "anoisesrc=d=0.4:c=pink:a=0.7[n];[n]bandpass=f=2200:width_type=h:w=2600,afade=t=in:d=0.12,afade=t=out:st=0.14:d=0.26,volume=0.8[o]",
})
# 8-bit square-wave sounds for the pixel videos (own synth, licence-free); keys = scripts/sfx.py cue kinds
SQ = "sgn(sin(2*PI*({f})*t))*{a}"
RECIPES.update({
    "blip": f"aevalsrc='{SQ.format(f='900+5000*t', a=0.3)}':d=0.12[a];[a]afade=t=out:st=0.05:d=0.07[o]",
    "zap": f"aevalsrc='{SQ.format(f='1900-5200*t', a=0.3)}':d=0.3[a];[a]afade=t=out:st=0.1:d=0.2[o]",
    "crack": "anoisesrc=d=0.3:c=white:a=0.7[n];[n]highpass=f=2500,afade=t=out:st=0.02:d=0.25[o]",
    "riser": f"aevalsrc='{SQ.format(f='300+900*t', a=0.22)}':d=1.2[a];[a]afade=t=in:d=0.8,afade=t=out:st=1.0:d=0.2[o]",
    "rip": "anoisesrc=d=0.5:c=white:a=0.6[n];[n]bandpass=f=3000:width_type=h:w=4000,tremolo=f=40:d=0.8,afade=t=out:st=0.3:d=0.2[o]",
    "gulp": "aevalsrc='sin(2*PI*(260-300*t)*t)*0.6':d=0.22[a];[a]afade=t=out:st=0.08:d=0.14[o]",
    "chime": "sine=f=1568:d=0.5[a];sine=f=2093:d=0.5[b];[a][b]amix=inputs=2:normalize=0,volume=0.7,afade=t=out:st=0.05:d=0.45[o]",
    "creak": f"aevalsrc='{SQ.format(f='140+60*sin(20*t)', a=0.2)}':d=0.5[a];[a]afade=t=in:d=0.1,afade=t=out:st=0.3:d=0.2[o]",
    "hit": "sine=f=90:d=0.4[a];anoisesrc=d=0.4:c=pink:a=0.4[n];[a]volume=1.2,afade=t=out:st=0.03:d=0.35[a1];[n]lowpass=f=500,afade=t=out:st=0:d=0.2[n1];[a1][n1]amix=inputs=2:normalize=0[o]",
    "alarm": f"aevalsrc='{SQ.format(f='700+300*sgn(sin(2*PI*6*t))', a=0.28)}':d=0.5[a];[a]afade=t=out:st=0.35:d=0.15[o]",
    "tick": f"aevalsrc='{SQ.format(f='1500', a=0.4)}':d=0.04[a];[a]afade=t=out:st=0.01:d=0.03[o]",
    "boing": "aevalsrc='sin(2*PI*(200+400*sin(2*PI*4*t))*t)*0.5':d=0.4[a];[a]afade=t=out:st=0.15:d=0.25[o]",
    "rewind": "anoisesrc=d=0.8:c=pink:a=0.5[n];[n]highpass=f=1200,tremolo=f=22:d=0.9,afade=t=in:d=0.1,afade=t=out:st=0.6:d=0.2[o]",
})


def make(name, out_path):
    flt = RECIPES[name]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-filter_complex", flt, "-map", "[o]", "-ac", "2", "-ar", "44100", str(out_path)], check=True, timeout=60)
    return str(out_path)
