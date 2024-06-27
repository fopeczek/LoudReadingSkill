import requests
import whisper


class Speech2Text:
    run_locally = False
    local_model = None

    def __init__(self, run_locally=False):
        self.run_locally = run_locally
        if self.run_locally:
            self.local_model = whisper.load_model("medium")

    def get_transcript(self, sound) -> str:
        if self.run_locally:
            return self.local_model.transcribe(sound.get_sample_as_np_array(), language='pl')['text'].strip()
        else:
            try:
                return requests.get("http://localhost:8000/request/", data=sound.json()).text.strip()
            except requests.exceptions.ConnectionError:
                raise ConnectionError("Could not connect to the server")
