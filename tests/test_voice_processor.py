import pytest
from unittest.mock import patch

from input.voice_processor import VoiceProcessor


@pytest.fixture
def processor():
    return VoiceProcessor()


async def test_transcribe_returns_string(processor):
    with patch.object(processor, "_run_whisper", return_value="Baue mir ein Login Feature"):
        result = await processor.transcribe("/tmp/test.ogg")
        assert result == "Baue mir ein Login Feature"


async def test_transcribe_empty_audio(processor):
    with patch.object(processor, "_run_whisper", return_value=""):
        result = await processor.transcribe("/tmp/empty.ogg")
        assert result == ""
