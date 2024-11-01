from client.iface import ISpeech2Text, IText2Speech
from .iface_scoring import IRespeak
from .text2speech_gtts import getText2Speech


def get_real_respeak_server(s2t: ISpeech2Text) -> IRespeak:
    from core.iface_scoring import IRespeak

    class RespeakServer(IRespeak):
        _s2t: ISpeech2Text
        _t2s: IText2Speech

        def __init__(
            self, s2t: ISpeech2Text, model: str = "tts_models/pl/mai_female/vits"
        ):
            print("Starting RespeakServer...")
            self._s2t = s2t
            self._t2s = getText2Speech(model)
            if self._t2s.check():
                print("Done.")
            else:
                raise RuntimeError("Failed to initialize Text2Speech server")

        def respeak(self, text: str) -> tuple[bool, str]:
            # print(f"Sending text to respeak: '{text}'...")
            ans = self._respeak_sync(text)
            # print(f"Respeak done: '{ans[1]}'")
            return ans

        def _respeak_sync(self, text: str) -> tuple[bool, str]:
            voice_sample = self._t2s.get_sound(text)
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
