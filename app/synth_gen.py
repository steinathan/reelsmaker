import os
import shutil
import uuid
from base64 import b64encode
from typing import Literal

from elevenlabs import Voice, VoiceSettings, save
from elevenlabs.client import ElevenLabs
from loguru import logger
from pydantic import BaseModel

from app import tiktokvoice
from app.config import speech_cache_path
from app.utils.path_util import search_file

VOICE_PROVIDER = Literal["elevenlabs", "tiktok"]


class SynthConfig(BaseModel):
    voice_provider: VOICE_PROVIDER = "tiktok"
    voice: str = "en_male_narration"


class SynthGenerator:
    def __init__(self, cwd: str, config: SynthConfig):
        self.config = config
        self.cwd = cwd
        self.cache_key: str | None = None
        self.eleven_voice_id = "ALDM8G793G6dq21Vj1Jm"

        self.base = os.path.join(self.cwd, "audio_chunks")

        os.makedirs(self.base, exist_ok=True)

        self.client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
        )

    def set_speech_props(self):
        self.speech_path = os.path.join(self.base, f"{uuid.uuid4()}.mp3")
        text_hash = b64encode(self.text.encode("ascii")).decode("utf-8")

        if self.config.voice_provider == "elevenlabs":
            self.cache_key = f"{self.eleven_voice_id}_{text_hash}"

        elif self.config.voice_provider == "tiktok":
            self.cache_key = f"{self.config.voice}_{text_hash}"

    async def generate_with_eleven(self, text: str) -> str:
        voice = Voice(
            voice_id=self.eleven_voice_id,
            settings=VoiceSettings(
                stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True
            ),
        )

        audio = self.client.generate(
            text=text, voice=voice, model="eleven_multilingual_v2", stream=False
        )

        save(audio, self.speech_path)

        return self.speech_path

    async def generate_with_tiktok(self, text: str) -> str:
        tiktokvoice.tts(text, voice=str(self.config.voice), filename=self.speech_path)
        return self.speech_path

    async def cache_speech(self, text: str):
        if not self.cache_key:
            logger.warning("Skipping speech cache because it is not set")
            return

        speech_path = os.path.join(speech_cache_path, f"{self.cache_key}.mp3")
        shutil.copy2(self.speech_path, speech_path)

    async def generate_audio(self, text: str) -> str:
        self.text = text
        self.set_speech_props()

        cached_speech = search_file(speech_cache_path, self.cache_key)

        if cached_speech:
            logger.info(f"Found speech in cache: {cached_speech}")
            shutil.copy2(cached_speech, self.speech_path)
            return cached_speech

        logger.info(f"Synthesizing text: {text}")

        genarator = (
            self.generate_with_eleven
            if self.config.voice_provider == "elevenlabs"
            else self.generate_with_tiktok
        )

        speech_path = await genarator(text)
        await self.cache_speech(text)

        return speech_path
