from __future__ import annotations

import datetime
import json
from pathlib import Path

from pydantic import BaseModel, Field


class ScoreDO(BaseModel):
    respeak_accuracy: float = 0.0
    correct_accuracy: float = 0.0
    effort_done: float = 0.0
    thinking_time: float = 0.0
    speaking_time: float = 0.0
    user_answer: str = ""
    timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.now
    )  # Because otherwise datetime.now() would be evaluated only once, at the import time
    saved_audio: Path = Path("")
    time_penalty: float = 0.0
    correct_sentence: str = ""
    respeak_sentence: str = ""
    flag_correct: bool = True
    respeak_words: list[bool] = []
    correct_words: list[bool] = []

    def __le__(self, other: ScoreDO):  # To be able to use heapq
        return self.overall_score <= other.overall_score

    @property
    def overall_score(self) -> float:
        return self.accuracy * self.time_penalty

    @property
    def words(self) -> list[bool]:
        return self.correct_words if self.flag_correct else self.respeak_words

    @property
    def accuracy(self) -> float:
        return self.correct_accuracy if self.flag_correct else self.respeak_accuracy

    @property
    def effort(self) -> float:
        return self.effort_done * self.accuracy


class TotalScoreDO(BaseModel):
    accuracy: float = 0.0
    effort_done: float = 0.0
    thinking_time: float = 0.0
    speaking_time: float = 0.0
    total_questions: int = 0
    story_index: int = 0
    _scores_file: Path

    @staticmethod
    def LoadScores(scores_file: Path) -> TotalScoreDO:
        json_text = scores_file.read_text()
        ans = TotalScoreDO(**json.loads(json_text))
        ans.set_scores_file(scores_file)
        return ans

    def set_scores_file(self, scores_file: Path):
        self._scores_file = scores_file

    def add_score(self, score: ScoreDO, increase_story_index: bool = False):
        self.accuracy += score.accuracy
        self.effort_done += score.effort
        self.thinking_time += score.thinking_time
        self.speaking_time += score.speaking_time
        self.total_questions += 1
        if increase_story_index:
            self.story_index += 1
        self.save()

    def save(self):
        self._scores_file.write_text(self.model_dump_json(indent=4))

    def clear(self):
        self.accuracy = 0.0
        self.effort_done = 0.0
        self.thinking_time = 0.0
        self.speaking_time = 0.0
        self.total_questions = 0
        self.story_index = 0
        self.save()


class ScoreHistoryDO(BaseModel):
    history: list[ScoreDO] = []
    _sentences: dict[str, list[ScoreDO]]  # A dictionary of sentences and their scores

    def __init__(self, **data):
        super().__init__(**data)
        self._sentences = {}

    def scores_by_sentence(self, sentence: str) -> list[ScoreDO]:
        return self._sentences.get(sentence, [])

    def add_score(self, score: ScoreDO, correct_answer: str):
        self.history.append(score)
        if correct_answer not in self._sentences:
            self._sentences[correct_answer] = []
        self._sentences[correct_answer].append(score)
