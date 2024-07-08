from fastapi import FastAPI
from core import VoiceSample, get_max_gpu_memory, guess_whisper_model

app = FastAPI()


class Transcribe:
    _model: "whisper.model"  # noqa: F821

    def __init__(self, whisper_model: str = "auto"):
        try:
            import whisper
        except ImportError:
            raise ImportError(
                "In order to run the server, you need to have whisper installed locally."
            )
        if whisper_model == "auto":
            whisper_model = guess_whisper_model(get_max_gpu_memory() / 1024 / 1024)
            print(
                f"Auto-detected best whisper model based on amount of free memory on GPU: {whisper_model}"
            )
        self._model = whisper.load_model(whisper_model)

    def get_transcript(self, sound: VoiceSample) -> str:
        return self._model.transcribe(sound.get_sample_as_np_array(), language="pl")[
            "text"
        ].strip()


@app.get("/request/")
async def request(audio: VoiceSample):
    global transcribe
    out = transcribe.get_transcript(audio)
    print(out)
    return out


@app.get("/")
async def root():
    return {"message": "Hello, use /request/ to send a voice sample to transcribe."}


def init():
    try:
        import whisper  # noqa: F401
    except ImportError:
        print("In order to run the server, you need to have whisper installed locally.")
        return

    global transcribe
    transcribe = Transcribe()


if __name__ == "__main__":
    init()
