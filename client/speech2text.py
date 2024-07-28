import requests
from pydantic import AnyUrl
from urllib.parse import urlparse
from core import guess_whisper_model, get_max_gpu_memory
from .iface import ISpeech2Text


class Speech2Text(ISpeech2Text):
    _run_locally: bool
    _local_model = None
    _remote_address: AnyUrl

    def __init__(self, server_url: AnyUrl, run_locally, whisper_model: str = "auto"):
        self._run_locally = run_locally
        if not self._run_locally:
            try:
                import whisper
            except ImportError:
                run_locally = True
            if self._run_locally:
                if whisper_model == "auto":
                    whisper_model = guess_whisper_model(
                        get_max_gpu_memory() / 1024 / 1024
                    )
                    print(
                        f"Auto-detected best whisper model based on amount of free memory on GPU: {whisper_model}"
                    )
                self._local_model = whisper.load_model(whisper_model)

        if isinstance(server_url, str):
            url = urlparse(server_url)
            if url.scheme != "http" and url.scheme != "https" and url.scheme != "":
                raise ValueError(
                    f"Server URL must have http or https scheme, not {url.scheme}."
                )
            if url.scheme == "":
                server_url = AnyUrl(f"http://{server_url}")
            else:
                server_url = AnyUrl(server_url)

        assert isinstance(server_url, AnyUrl)
        self._remote_address = server_url

    def get_transcript(self, sound) -> (bool, str):
        if self._run_locally:
            return True, self._local_model.transcribe(
                sound.get_sample_as_np_array(), language="pl"
            )["text"].strip()
        else:
            try:
                return True, requests.get(
                    f"{self._remote_address}/request/", data=sound.json()
                ).text.strip()
            except requests.exceptions.ConnectionError:
                return False, "Could not connect to the server. "

    def check(self) -> bool:
        if self._run_locally:
            return True
        try:
            out = requests.get(f"{self._remote_address}/request/", data={}).text
            return out != ""
        except requests.exceptions.ConnectionError:
            return False
