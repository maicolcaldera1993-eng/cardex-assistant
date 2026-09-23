"""The assistant's voice for the automatic mode: Edge neural TTS (free), MP3 kept in memory and served by
/api/tts/<key>.mp3. The browser plays it and keeps the microphone muted meanwhile, so the assistant never hears
itself. Rehearsal quality; the final demo may swap the voice."""
from __future__ import annotations

import hashlib

VOICE = "en-GB-SoniaNeural"


class TextToSpeech:
    def __init__(self, voice: str = VOICE):
        self.voice = voice
        self.cache: dict[str, bytes] = {}

    async def synth(self, text: str) -> tuple[str, float]:
        """Returns (key, estimated seconds). The audio is synthesised once per sentence and cached."""
        key = hashlib.sha1(f"{self.voice}|{text}".encode("utf-8")).hexdigest()[:16]
        if key not in self.cache:
            import edge_tts
            comm = edge_tts.Communicate(text, self.voice, rate="-4%")
            chunks = [c["data"] async for c in comm.stream() if c["type"] == "audio"]
            self.cache[key] = b"".join(chunks)
        seconds = round(len(text.split()) / 2.5 + 0.6, 1)      # ~150 words per minute
        return key, seconds


TTS = TextToSpeech()
