"""Generates the customer side of the two-voice rehearsal calls from the scripts in eval/duets/*.json:
one clip per customer line (Edge neural voice with the customer's accent reading English), 16 kHz mono PCM16,
plus samples/duet/<id>/script.json with, for every line, the operator's cue (what to say before clicking it)
and what the assistant is expected to do. Rehearsal quality only; the final sample calls will use approved
scripts and ElevenLabs.

    .venv/Scripts/python eval/make_duet.py              # every script; clips already synthesised for the same text are kept
    .venv/Scripts/python eval/make_duet.py lena-berlin  # one script
"""
import asyncio
import json
import sys
from pathlib import Path

import miniaudio

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "eval" / "duets"
OUT = ROOT / "samples" / "duet"


async def build(script_path: Path) -> None:
    import edge_tts
    spec = json.loads(script_path.read_text(encoding="utf-8"))
    out = OUT / spec["id"]
    out.mkdir(parents=True, exist_ok=True)
    old = {}
    if (out / "script.json").exists():
        old = {l["n"]: l for l in json.loads((out / "script.json").read_text(encoding="utf-8"))["lines"]}
    lines = []
    for i, line in enumerate(spec["lines"], 1):
        wav = out / f"{i:02d}.wav"
        prev = old.get(i)
        if prev and prev["text"] == line["text"] and prev.get("voice", spec["voice"]) == spec["voice"] and wav.exists():
            secs = prev["seconds"]
            status = "kept"
        else:
            mp3 = out / f"{i:02d}.mp3"
            await edge_tts.Communicate(line["text"], spec["voice"], rate="-8%").save(str(mp3))
            dec = miniaudio.decode_file(str(mp3), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=16000)
            miniaudio.wav_write_file(str(wav), miniaudio.DecodedSoundFile(wav.stem, 1, 16000, miniaudio.SampleFormat.SIGNED16, dec.samples))
            mp3.unlink()
            secs = round(len(dec.samples) / 16000, 1)
            status = "new"
        lines.append({"n": i, "file": wav.name, "seconds": secs, "text": line["text"], "voice": spec["voice"],
                      "cue": line.get("cue", ""), "expect_it": line.get("expect_it", "")})
        print(f"{spec['id']} {i:02d} {secs:4.1f}s {status:4s} {line['text'][:60]}")
    (out / "script.json").write_text(json.dumps({
        "id": spec["id"], "title_it": spec["title_it"], "title_en": spec["title_en"], "voice": spec["voice"],
        "customer_lang": spec.get("customer_lang", "en"), "accent": spec.get("accent", ""), "lines": lines},
        ensure_ascii=False, indent=2), encoding="utf-8")


async def main() -> None:
    wanted = set(sys.argv[1:])
    for f in sorted(SCRIPTS.glob("*.json")):
        if not wanted or f.stem in wanted:
            await build(f)


asyncio.run(main())
