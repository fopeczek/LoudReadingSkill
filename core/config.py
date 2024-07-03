from pathlib import Path

from pydantic import AnyUrl, BaseModel

from core import create_and_load_file


class ConfigData(BaseModel):
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


class Config:
    _config_path: Path
    _config_data: ConfigData

    def __init__(self, config_path: Path = Path("config.json")):
        self._config_path = config_path
        self._config_data = ConfigData()
        self.load_config()

    def load_config(self):
        if not self._config_path.exists():
            self.save_config()

        self._config_data = ConfigData(**create_and_load_file(self._config_path, {}))

    def save_config(self):
        with open(self._config_path, "w") as f:
            json_dump = self._config_data.model_dump_json(indent=4)
            f.write(json_dump)

    def get_config(self) -> ConfigData:
        return self._config_data
