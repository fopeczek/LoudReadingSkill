from client.iface import IText2Speech
from overrides import overrides
from typing import Optional
import tempfile
from core import voice_sample_from_wav, VoiceSample
from pathlib import Path


def getText2Speech(model: str = None) -> IText2Speech:
    return Text2Speech_Local(model)


class Text2Speech_Local(IText2Speech):
    _server: Optional[IText2Speech]
    _model: Optional[str]

    def __init__(self, model: str = None):
        self._server = None
        if model is None:
            self._model = "tts_models/pl/mai_female/vits"
        else:
            self._model = model

    @overrides
    def get_sound(self, text: str) -> VoiceSample:
        if self._server is None:
            raise RuntimeError("Server not initialized")
        return self._server.get_sound(text)

    def check(self) -> bool:
        try:
            from TTS.api import TTS
            import torch
        except ImportError:
            return False

        class Text2Speech_Pimpl(IText2Speech):
            _tts: TTS

            def __init__(self, model: str):
                self._tts = TTS(model_name=model, progress_bar=False).to(
                    "cuda" if torch.cuda.is_available() else "cpu"
                )

            @overrides
            def get_sound(self, text: str) -> VoiceSample:
                tmp = tempfile.NamedTemporaryFile(suffix=".wav")
                self._tts.tts_to_file(text, file_path=tmp)
                voice_sample = voice_sample_from_wav(Path("/tmp/test.wav"))
                return voice_sample

            @overrides
            def check(self) -> bool:
                return True

        self._server = Text2Speech_Pimpl(self._model)
        return True
