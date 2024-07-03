import os
from pathlib import Path
from .util import create_and_load_file


class Config:
    _config_path: Path
    _config: dict[str, any]

    def __init__(self, config_path: Path = Path("config.json")):
        self._config_path = config_path
        self._config = {
            "story mode": False,
            "correct min accuracy": 0.8,
            "correct min speed": 0.5,
            "incorrect max accuracy": 0.4,
            "incorrect max speed": 0.4,
            "max answer per question": 1,
            "max new question rolls": 1,
            "run whisper locally": False,
            "whisper host": "192.168.42.5:8000",
            "questions file": "data/sentences.txt",
            "answers file": "data/answers.json",
            "scores file": "data/scores.json",
            "user recordings directory": "data/audio/user",
        }
        self.load_config()

    def load_config(self):
        self._config = create_and_load_file(self._config_path, self._config)
