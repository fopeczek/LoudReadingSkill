from client.iface import IText2Speech
from overrides import overrides
from typing import Optional
import tempfile
from core import voice_sample_from_wav, VoiceSample
from pathlib import Path
from pydub import AudioSegment


def getText2Speech(model: str = None) -> IText2Speech:
    return Text2Speech_GoogleTTS(model)


class Text2Speech_GoogleTTS(IText2Speech):
    _server: Optional[IText2Speech]
    _model: Optional[str]

    def __init__(self, model: str = None):
        self._server = None
        self._model = model

    @overrides
    def get_sound(self, text: str) -> VoiceSample:
        if self._server is None:
            raise RuntimeError("Server not initialized")
        return self._server.get_sound(text)

    def check(self) -> bool:
        try:
            from gtts import gTTS
        except ImportError:
            return False

        class Text2Speech_Pimpl(IText2Speech):
            _model: Optional[str]

            def __init__(self, model: str = None):
                self._model = model

            @overrides
            def get_sound(self, text: str) -> VoiceSample:
                tts = gTTS(text=text, lang="pl")
                tmp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                tts.save(tmp_mp3.name)

                # Transcode MP3 to WAV
                audio = AudioSegment.from_mp3(tmp_mp3.name)
                tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                audio.export(tmp_wav.name, format="wav")

                voice_sample = voice_sample_from_wav(Path(tmp_wav.name))
                return voice_sample

            @overrides
            def check(self) -> bool:
                return True

        self._server = Text2Speech_Pimpl(self._model)
        return True


def test_Text2Speech_GoogleTTS():
    tts = Text2Speech_GoogleTTS()
    assert tts.check()
    voice_sample = tts.get_sound("Hello, world!")
    assert voice_sample.frame_rate == 24000
    assert voice_sample.sample_width == 2
    assert len(voice_sample.data) > 0
    voice_sample.save(Path("/tmp/test.wav"))


if __name__ == "__main__":
    test_Text2Speech_GoogleTTS()
    print("Text2Speech_GoogleTTS OK")
