from __future__ import annotations

import asyncio
import logging
import shutil

logger = logging.getLogger(__name__)


class VoiceProcessor:
    def __init__(self, model: str = "base", language: str = "de") -> None:
        self._model = model
        self._language = language

    async def transcribe(self, audio_path: str) -> str:
        return await self._run_whisper(audio_path)

    async def _run_whisper(self, audio_path: str) -> str:
        whisper_bin = shutil.which("whisper")
        if whisper_bin:
            proc = await asyncio.create_subprocess_exec(
                whisper_bin, audio_path,
                "--model", self._model,
                "--language", self._language,
                "--output_format", "txt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()

        try:
            import whisper
            model = whisper.load_model(self._model)
            result = model.transcribe(audio_path, language=self._language)
            return result["text"].strip()
        except ImportError:
            logger.error("Neither whisper CLI nor Python whisper package available")
            return ""
        except Exception as e:
            logger.error("Whisper transcription failed: %s", e)
            return ""
