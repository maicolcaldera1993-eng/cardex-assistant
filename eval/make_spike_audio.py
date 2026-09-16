"""Generates the spike audio set: synthetic voices reading Sereni model names and
part codes, in Italian and in accented English. Output: eval/spike_audio/*.wav
(16 kHz mono PCM16) plus manifest.json with the expected models and codes.

Voices:
  - Windows SAPI: Microsoft Elsa (it-IT), Microsoft Zira (en-US)  -> direct WAV
  - Edge neural voices via edge-tts: de-DE, en-AU, tr-TR, fr-FR reading English
    -> mp3, decoded and resampled with miniaudio

Run: .venv/Scripts/python eval/make_spike_audio.py
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import miniaudio

OUT = Path(__file__).parent / "spike_audio"
OUT.mkdir(exist_ok=True)

EXPECTED_MODELS = ["Marea 2 Plus", "Giglio 1 Plus", "Monda 65 Digit", "Onda MB2", "Vaniglia"]
EXPECTED_CODES = ["GE-2140", "GE-2150", "CA-1180", "EL-3010", "ID-4010", "VA-5015", "MC-7010", "GE-2410"]

SCRIPT_EN = (
    "Hi, this is Jonas calling from Cafe Berlin. "
    "We have a Marea 2 Plus, the Vaniglia edition. "
    "The coffee comes out thin and fast, like water. "
    "Last year we ordered the group gasket, the code is G E twenty-one forty. "
    "We also need the shower screen, G E two one five zero. "
    "For the heating element the invoice says C A eleven eighty. "
    "The control board is E L three zero one zero, and the pump is I D forty ten. "
    "The steam valve seal kit is V A fifty fifteen. "
    "In the other shop we have a Giglio 1 Plus and a Monda 65 Digit grinder, the burrs are M C seventy ten. "
    "And the Onda MB2 has a probe alarm. The Onda gasket is G E twenty-four ten."
)

SCRIPT_IT = (
    "Buongiorno, sono Marco del bar Centrale. "
    "Abbiamo una Marea 2 Plus, edizione Vaniglia. "
    "Il caffè esce slavato, come acqua. "
    "L'anno scorso abbiamo ordinato la guarnizione sottocoppa, codice gi e ventuno quaranta. "
    "Ci serve anche la doccetta, gi e due uno cinque zero. "
    "Per la resistenza sulla fattura c'è scritto ci a undici ottanta. "
    "La centralina è e elle tre zero uno zero, e la pompa è i di quaranta dieci. "
    "Il kit guarnizioni vapore è vu a cinquanta quindici. "
    "Nell'altro locale abbiamo una Giglio 1 Plus e un macinacaffè Monda 65 Digit, le macine sono emme ci settanta dieci. "
    "E la Onda MB2 ha l'allarme sonda. La guarnizione della Onda è gi e ventiquattro dieci."
)

SAPI = [
    ("it_elsa", "Microsoft Elsa Desktop", SCRIPT_IT),
    ("en_us_zira", "Microsoft Zira Desktop", SCRIPT_EN),
]

EDGE = [
    ("en_de_katja", "de-DE-KatjaNeural", SCRIPT_EN),
    ("en_au_natasha", "en-AU-NatashaNeural", SCRIPT_EN),
    ("en_tr_emel", "tr-TR-EmelNeural", SCRIPT_EN),
    ("en_fr_denise", "fr-FR-DeniseNeural", SCRIPT_EN),
]


def sapi_to_wav(name: str, voice: str, text: str) -> Path:
    raw = OUT / f"{name}_raw.wav"
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SelectVoice('{voice}'); $s.Rate = 0; "
        f"$s.SetOutputToWaveFile('{raw}'); "
        f"$s.Speak([IO.File]::ReadAllText('{OUT / (name + '.txt')}', [Text.Encoding]::UTF8)); $s.Dispose()"
    )
    (OUT / f"{name}.txt").write_text(text, encoding="utf-8")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    return raw


async def edge_to_mp3(name: str, voice: str, text: str) -> Path:
    import edge_tts
    mp3 = OUT / f"{name}.mp3"
    await edge_tts.Communicate(text, voice, rate="-5%").save(str(mp3))
    return mp3


def to_pcm16k(src: Path, dst: Path) -> float:
    dec = miniaudio.decode_file(str(src), output_format=miniaudio.SampleFormat.SIGNED16,
                                nchannels=1, sample_rate=16000)
    pcm = bytes(dec.samples)
    miniaudio.wav_write_file(str(dst), miniaudio.DecodedSoundFile(
        dst.stem, 1, 16000, miniaudio.SampleFormat.SIGNED16, dec.samples))
    return len(pcm) / 2 / 16000


def main() -> None:
    manifest = []
    for name, voice, text in SAPI:
        raw = sapi_to_wav(name, voice, text)
        secs = to_pcm16k(raw, OUT / f"{name}.wav")
        raw.unlink()
        manifest.append({"file": f"{name}.wav", "voice": voice, "lang": "it" if name.startswith("it") else "en",
                         "seconds": round(secs, 1), "models": EXPECTED_MODELS, "codes": EXPECTED_CODES})
        print(f"{name}: {secs:.1f}s")
    for name, voice, text in EDGE:
        mp3 = asyncio.run(edge_to_mp3(name, voice, text))
        secs = to_pcm16k(mp3, OUT / f"{name}.wav")
        mp3.unlink()
        manifest.append({"file": f"{name}.wav", "voice": voice, "lang": "en",
                         "seconds": round(secs, 1), "models": EXPECTED_MODELS, "codes": EXPECTED_CODES})
        print(f"{name}: {secs:.1f}s")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
