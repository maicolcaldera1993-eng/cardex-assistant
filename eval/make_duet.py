"""Generates the customer side of a two-voice rehearsal call: one clip per line, German-accented
English (Edge neural voice de-DE reading English text), 16 kHz mono PCM16, plus script.json.
Rehearsal quality only; the final sample calls will use approved scripts and ElevenLabs.

    .venv/Scripts/python eval/make_duet.py
"""
import asyncio
import json
from pathlib import Path

import miniaudio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples" / "duet" / "jonas-marea"
OUT.mkdir(parents=True, exist_ok=True)
VOICE = "de-DE-ConradNeural"

LINES = [
    "Hello, good morning. This is Jonas, from Cafe Berlin, in Hamburg.",
    "We have a problem with our coffee machine. It is the Marea 2 Plus, the vanilla one, the cream colour.",
    "Since maybe two weeks, the coffee comes out very thin and fast. Like water. No body, no crema.",
    "A double shot takes maybe fifteen, eighteen seconds. Before it was longer.",
    "The last cleaning with the tablet and the blind filter... honestly, I think two or three weeks ago.",
    "Okay, I did the backflush now, five times with the tablet. It is still weak.",
    "I unscrewed the shower screen. It has white scale on it, but the holes are fine, not damaged.",
    "I put it in the descaler and cleaned it. Now the coffee is much better, yes. Thank you.",
    "Also, when I lock the portafilter it goes very far to the right, and water comes around. Last year we ordered the gasket, the code on the invoice is G E twenty-one forty.",
    "The serial number is zero four seven, two one nine.",
    "One more thing. The control board, on the old one is written E L three zero one zero. Is it still the same part?",
    "Okay, perfect. Please send the gasket and the tablets to Hamburg. Thank you, goodbye.",
]


async def main() -> None:
    import edge_tts
    script = []
    for i, text in enumerate(LINES, 1):
        mp3 = OUT / f"{i:02d}.mp3"
        await edge_tts.Communicate(text, VOICE, rate="-8%").save(str(mp3))
        dec = miniaudio.decode_file(str(mp3), output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=16000)
        wav = OUT / f"{i:02d}.wav"
        miniaudio.wav_write_file(str(wav), miniaudio.DecodedSoundFile(wav.stem, 1, 16000, miniaudio.SampleFormat.SIGNED16, dec.samples))
        mp3.unlink()
        secs = len(dec.samples) / 16000
        script.append({"n": i, "file": wav.name, "seconds": round(secs, 1), "text": text})
        print(f"{i:02d} {secs:4.1f}s  {text[:70]}")
    (OUT / "script.json").write_text(json.dumps({
        "id": "jonas-marea", "title_it": "Jonas, Cafe Berlin (tedesco): Marea 2 Plus, caffè slavato",
        "title_en": "Jonas, Cafe Berlin (German): Marea 2 Plus, weak coffee",
        "voice": VOICE, "customer_lang": "en", "accent": "de", "lines": script}, ensure_ascii=False, indent=2), encoding="utf-8")


asyncio.run(main())
