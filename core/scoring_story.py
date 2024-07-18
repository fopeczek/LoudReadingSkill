import datetime
from pathlib import Path

from overrides import overrides

from core import ConfigDataDO
from .iface_scoring import IScoring
from .scoring_arcade import calc_time_penalty
from .scoring_serialization import ScoreHistoryDO, ScoreDO
from .sentence_accuracy import score_sentence


class Scoring_Story(IScoring):
    """Scoring class for the story reading mode of the game, i.e. the one where sentences are presented in a fixed order, and user progresses through them by reading.

    Class is not responsible for thresholding the scores to decide if the sentence is correct or not. Calee is responsible to decide that.

    Class provives a Score object for each stored sentence, that can be used to calculate the binary score and whether or not to progress to the next sentence.

    Invariants:
    * All class members are always serialized to a file.
    """

    _config: ConfigDataDO

    _score_history: ScoreHistoryDO
    _last_index: int = 0

    _story: list[str]  # List of all the sentences in the story, in order.

    def __init__(self, config: ConfigDataDO, last_index: int = 0):
        self._config = config
        self._score_history = config.load_history()
        self._last_index = last_index

        self._story = self.config.load_questions()

    @property
    def config(self):
        return self._config

    @overrides
    def get_next_sentence(self) -> str:
        """Returns the sentence that the user should be asked next."""
        self._last_index += 1
        return self._story[self._last_index - 1]

    @overrides
    def set_next_sentence(self, new_index: int):
        self._last_index = new_index

    @overrides
    def set_sentence_answer(
        self,
        sentence: str,
        user_answer: str,
        thinking_time: float,
        speaking_time: float,
        saved_audio_path: Path,
    ) -> ScoreDO:
        accuracy, words = score_sentence(
            correct_sentence=sentence, user_sentence=user_answer
        )
        time_penalty = calc_time_penalty(
            thinking_time=thinking_time,
            speaking_time=speaking_time,
            correct_sentence=sentence,
        )

        score = ScoreDO(
            accuracy=accuracy,
            thinking_time=thinking_time,
            speaking_time=speaking_time,
            user_answer=user_answer,
            timestamp=datetime.datetime.now(),
            saved_audio=saved_audio_path,
            time_penalty=time_penalty,
            words=words,
        )

        self._score_history.add_score(score, sentence)

        self.save()

        return score

    def save(self):
        """Saves the history of the scores. This function is called automatically after storing each answer."""
        self.config.save_history(self._score_history)
