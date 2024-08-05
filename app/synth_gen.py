import os
import uuid
from typing import Literal

from elevenlabs import Voice, VoiceSettings, save
from elevenlabs.client import ElevenLabs
from loguru import logger
from pydantic import BaseModel

from app import tiktokvoice


class SynthConfig(BaseModel):
    voice_provider: Literal["elevenlabs", "tiktok"] = "tiktok"
    voice: str = "en_male_narration"


class SynthGenerator:
    def __init__(self, cwd: str, config: SynthConfig):
        self.config = config
        self.cwd = cwd

        self.base = os.path.join(self.cwd, "audio_chunks")

        os.makedirs(self.base, exist_ok=True)

        self.client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY"), 
        )

    def set_filename(self):
        self.filename = os.path.join(self.base, f"{uuid.uuid4()}.mp3")

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

        save(audio, self.filename)

        return self.filename

    async def generate_with_tiktok(self, text: str) -> str:
        tiktokvoice.tts(text, voice=str(self.config.voice), filename=self.filename)
        return self.filename

    async def generate_audio(self, text: str) -> str:
        self.set_filename()
        logger.info(f"Synthesizing text: {text}")
        if self.config.voice_provider == "tiktok":
            return await self.generate_with_tiktok(text)
        else:
            return await self.generate_with_eleven(text)
