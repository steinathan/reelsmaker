import os
import uuid

from elevenlabs import Voice, VoiceSettings
from loguru import logger

from elevenlabs.client import ElevenLabs
from elevenlabs import save

from app import tiktokvoice


class SynthGenerator:
    def __init__(self, cwd, voice="en_male_narration"):
        self.cwd = cwd
        self.voice = voice
        self.base = os.path.join(self.cwd, "audio_chunks")
        os.makedirs(self.base, exist_ok=True)

        self.client = ElevenLabs(
            api_key=os.getenv("ELEVEN_API_KEY"),  # Defaults to ELEVEN_API_KEY
        )

    async def generate_with_eleven(self, text: str) -> str:
        self.voice = Voice(
            voice_id="pNInz6obpgDQGcFmaJgB",
            name="Adam",
            settings=VoiceSettings(
                stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True
            ),
        )
        audio = self.client.generate(
            text=text, voice=self.voice, model="eleven_multilingual_v2", stream=False
        )

        save(audio, self.filename)  # type: ignore

        return self.filename

    async def generate_audio(self, text: str) -> str:
        logger.info(f"Synthesizing text: {text}")
        self.filename = os.path.join(self.base, f"{uuid.uuid4()}.mp3")
        tiktokvoice.tts(text, voice=str(self.voice), filename=self.filename)
        return self.filename
        # return await self.generate_with_eleven(text)
