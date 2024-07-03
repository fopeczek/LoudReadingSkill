from pathlib import Path
import json

from dataclasses import dataclass

from pydantic import AnyUrl

from core import create_and_load_file


@dataclass
class ConfigData:
    story_mode: bool = True
    correct_min_accuracy: float = 0.8
    correct_min_speed: float = 0.5
    incorrect_max_accuracy: float = 0.4
    incorrect_max_speed: float = 0.4
    max_answers_per_question: int = 1
    max_new_question_rolls: int = 1
    run_whisper_locally: bool = False
    whisper_host: AnyUrl = AnyUrl("http://192.168.42.5:8000")
    questions_file: Path = Path("data/sentences.txt")
    answers_file: Path = Path("data/answers.json")
    scores_file: Path = Path("data/scores.json")
    recordings_directory: Path = Path("data/audio/user")

    @staticmethod
    def FromDict(d: dict):
        return ConfigData(
            d["story mode"],
            d["correct min accuracy"],
            d["correct min speed"],
            d["incorrect max accuracy"],
            d["incorrect max speed"],
            d["max answers per question"],
            d["max new question rolls"],
            d["run whisper locally"],
            AnyUrl(d["whisper host"]),
            Path(d["questions file"]),
            Path(d["answers file"]),
            Path(d["scores file"]),
            Path(d["user recordings directory"]),
        )

    def dict(self):
        return {
            "story mode": self.story_mode,
            "correct min accuracy": self.correct_min_accuracy,
            "correct min speed": self.correct_min_speed,
            "incorrect max accuracy": self.incorrect_max_accuracy,
            "incorrect max speed": self.incorrect_max_speed,
            "max answers per question": self.max_answers_per_question,
            "max new question rolls": self.max_new_question_rolls,
            "run whisper locally": self.run_whisper_locally,
            "whisper host": str(self.whisper_host),
            "questions file": str(self.questions_file),
            "answers file": str(self.answers_file),
            "scores file": str(self.scores_file),
            "user recordings directory": str(self.recordings_directory),
        }


class Config:
    _config_path: Path
    _config_data: ConfigData

    def __init__(self, config_path: Path = Path("config.json")):
        self._config_path = config_path
        self._config_data = ConfigData()
        self.load_config()

    def load_config(self):
        self._config_data = ConfigData.FromDict(
            create_and_load_file(self._config_path, self._config_data.dict())
        )

    def save_config(self):
        with open(self._config_path, "w") as f:
            f.write(json.dumps(self._config_data.dict(), indent=4))

    def get_config(self) -> ConfigData:
        return self._config_data
