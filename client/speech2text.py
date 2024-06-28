import requests
from pydantic import AnyUrl


class Speech2Text:
    _run_locally: bool = False
    _local_model = None
    _remote_address: AnyUrl

    def __init__(self, server_url: AnyUrl, run_locally=False):
        self._run_locally = run_locally
        if not self._run_locally:
            try:
                import whisper
            except ImportError:
                run_locally = True
            if self._run_locally:
                self._local_model = whisper.load_model("medium")

        if isinstance(server_url, str):
            server_url = AnyUrl(server_url)
        assert isinstance(server_url, AnyUrl)
        if server_url.scheme != "http" and server_url.scheme != "https":
            raise ValueError("Server URL must have http or https scheme.")
        if server_url.scheme == "":
            server_url = AnyUrl(f"http://{server_url}")
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
            print(out)
            return True
        except requests.exceptions.ConnectionError:
            return False
