from fastapi import FastAPI
from core.voice_sample import VoiceSample

app = FastAPI()


def guess_whisper_model(gpu_freemem_mb: int | float) -> str:
    """Source: https://github.com/openai/whisper"""
    if gpu_freemem_mb > 10000:
        return "large"
    elif gpu_freemem_mb > 5000:
        return "medium"
    elif gpu_freemem_mb > 2000:
        return "small"
    elif gpu_freemem_mb > 100:
        return "base"
    return ""


def get_max_gpu_memory() -> int:
    try:
        import pynvml

        pynvml.nvmlInit()
        max_mem = 0
        for idx in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(idx)
            info = pynvml.nvmlDeviceGetMemoryInfo(h)
            if max_mem < info.free:
                max_mem = info.free

        pynvml.nvmlShutdown()
        return max_mem
    except ImportError:
        raise ImportError(
            "In order to run the server, you need to have whisper installed locally."
        )


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
