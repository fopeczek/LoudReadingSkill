import json
from pathlib import Path

from pydantic import AnyUrl, BaseModel

from core import create_and_load_file_str
from .scoring_serialization import ScoreHistoryDO, TotalScoreDO


class ConfigDataDO(BaseModel):
    story_mode: bool = True
    thinking_time_multiplier: float = 1.0
    correct_overall_score_threshold: float = 0.8
    incorrect_overall_score_threshold: float = 0.4
    run_whisper_locally: bool = False
    max_new_question_rolls: int = 1
    max_answers_per_question: int = 2
    whisper_host: AnyUrl = AnyUrl("http://192.168.42.5:8000")
    questions_file: Path = Path("data/sentences.txt")
    answers_file: Path = Path("data/answers.json")
    scores_file: Path = Path("data/scores.json")
    recordings_directory: Path = Path("data/audio/user")
    history_file: Path = Path("data/history.json")

    def save(self, config_path: Path = Path("config.json")):
        if config_path is None:
            config_path = Path("config.json")
        config_path.write_text(self.model_dump_json(indent=4))

    def save_history(self, history_file: ScoreHistoryDO):
        self.history_file.write_text(history_file.model_dump_json(indent=4))

    def load_history(self) -> ScoreHistoryDO:
        if not self.history_file.exists():
            return ScoreHistoryDO()
        json_text = self.history_file.read_text()
        return ScoreHistoryDO(**json.loads(json_text))

    def load_questions(self) -> list[str]:
        return self.questions_file.read_text().split("\n")

    def load_total_scores(self) -> TotalScoreDO:
        if not self.scores_file.exists():
            ans = TotalScoreDO()
        else:
            json_text = self.scores_file.read_text()
            ans = TotalScoreDO(**json.loads(json_text))
        ans.set_scores_file(self.scores_file)
        return ans

    def save_total_scores(self, total_score: TotalScoreDO):
        self.scores_file.write_text(total_score.model_dump_json(indent=4))


def load_config(config_path: Path = Path("config.json")) -> ConfigDataDO:
    return ConfigDataDO(
        **create_and_load_file_str(config_path, ConfigDataDO().model_dump_json())
    )
