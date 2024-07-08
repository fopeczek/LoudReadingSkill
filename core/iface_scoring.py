from abc import ABC, abstractmethod
from pathlib import Path

from .scoring_serialization import ScoreDO


class IScoring(ABC):
    """This is a singleton class that decides the next sentence to be presented and judges user's answer.
    The class is not concerned with the thresholding of the scores, but only with the storage and retrieval of the scores.
    Consequently, the class is not concerned with TotalScore.
    """

    @abstractmethod
    def get_next_sentence(self) -> str:
        """Returns the next sentence to be preseneneted to the user."""
        pass

    @abstractmethod
    def set_sentence_answer(
        self,
        sentence: str,
        user_answer: str,
        thinking_time: float,
        speaking_time: float,
        saved_audio_path: Path,
    ) -> ScoreDO:
        """Sets the answer for the sentence."""
        pass
