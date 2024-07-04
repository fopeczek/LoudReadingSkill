import datetime
from pathlib import Path

from pydantic import BaseModel


class TotalScore(BaseModel):
    accuracy: float = 0.0
    speed: float = 0.0
    correct: float = 0.0
    incorrect: float = 0.0
    total_questions: float = 0.0
    story_index: int = 0


class Score(BaseModel):
    accuracy: float = 0.0
    time: float = 0.0
    user_answer: str = ""
    timestamp: datetime.datetime = datetime.datetime.now()


def check_directories():
    (Path.cwd() / "data/audio/user").mkdir(parents=True, exist_ok=True)


def get_resource_path(audio_file: Path | str) -> Path:
    current_file_path = Path(__file__)
    project_root = current_file_path.parent.parent
    return project_root / "data" / "audio" / audio_file
