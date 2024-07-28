from client.iface import ISpeech2Text
from .iface_scoring import IRespeak


def get_real_respeak_server(s2t: ISpeech2Text) -> IRespeak:
    from TTS.api import TTS
    import torch
    from core.voice_sample import test_voice_sample_from_wav
    from pathlib import Path
    from core.iface_scoring import IRespeak

    class RespeakServer(IRespeak):
        _s2t: ISpeech2Text
        _tts: TTS

        def __init__(
            self, s2t: ISpeech2Text, model: str = "tts_models/pl/mai_female/vits"
        ):
            print("Starting RespeakServer...")
            self._s2t = s2t
            self._tts = TTS(model_name=model, progress_bar=False).to(
                "cuda" if torch.cuda.is_available() else "cpu"
            )
            print("Done.")

        def respeak(self, text: str) -> tuple[bool, str]:
            print(f"Sending text to respeak: '{text}'...")
            ans = self._respeak_sync(text)
            print(f"Respeak done: '{ans[1]}'")
            return ans

        def _respeak_sync(self, text: str) -> tuple[bool, str]:
            self._tts.tts_to_file(text, file_path="/tmp/test.wav")
            voice_sample = test_voice_sample_from_wav(Path("/tmp/test.wav"))
            return self._s2t.get_transcript(voice_sample)

    return RespeakServer(s2t)


def get_fake_respeak_server() -> IRespeak:
    class FakeRespeakServer(IRespeak):
        def __init__(self, *args, **kwargs):
            pass

        def respeak(self, text: str) -> tuple[bool, str]:
            return True, text

    return FakeRespeakServer()


def get_respeak_server(s2t: ISpeech2Text) -> IRespeak:
    try:
        return get_real_respeak_server(s2t)
    except ImportError:
        return get_fake_respeak_server()
        # return get_real_respeak_server(s2t)


#
# def test_round_trip(text:str="Gdy w namiocie spotykała Ajoka, ze zdumieniem dostrzegała, że choć oboje robią to samo - pacjenci chłopca uśmiechają się do niego, a ci, przy których ona się krząta, starają się unikać jej wzroku."):
#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     tts = TTS(model_name="tts_models/pl/mai_female/vits", progress_bar=False).to(device)
#     tts.tts_to_file(text, file_path="/tmp/test.wav")
#     voice_sample = test_voice_sample_from_wav(Path("/tmp/test.wav"))
#     s2t = Speech2Text(AnyUrl("http://192.168.42.5:8000/"), False)
#     print(s2t.get_transcript(voice_sample))
#
#
# if __name__ == "__main__":
#     test_round_trip()
