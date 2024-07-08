from .scoring_serialization import ScoreHistoryDO, ScoreDO
from .iface_scoring import IScoring
from core import ConfigDataDO
import datetime
import numpy as np
from typing import Callable
from pathlib import Path
from overrides import overrides

from .sentence_accuracy import score_sentence
from .util import just_letters


def weighting_function(
        x0: float, weight0: float, x1: float, weight1: float
) -> Callable[[float], float]:
    """Returns a function that gives a weight to a given value x, based on the two points (x0, weight0) and (x1, weight1)."""
    slope = -np.log(weight0 / weight1) / (x0 - x1)
    amplitude = weight0 * np.exp(slope * x0)

    return lambda x: amplitude * np.exp(slope * x)


def calculate_timeout_from_sentence(correct_sentence: str) -> float:
    return len(just_letters(correct_sentence)) / 6 + 4


def calc_time_penalty(
        thinking_time: float, speaking_time: float, correct_sentence: str
) -> float:
    timeout = calculate_timeout_from_sentence(correct_sentence)
    if thinking_time < timeout:
        return 1
    if thinking_time > timeout * 10:
        return 0

    return (thinking_time - timeout) / (
            timeout * 9
    )  # Linear interpolation between the two timeouts.


class Scoring_Arcade(IScoring):
    """Scoring class for the arcade mode of the game, i.e. the one where each sentence is independent of the others.

    Class is not responsible for thresholding the scores to decide if the sentence is correct or not.

    Class provives a Score object for each stored sentence, that can be used to calculate the binary score.

    Invariants:
    * All class members are always serialized to a file.
    """

    _config: ConfigDataDO

    _score_history: ScoreHistoryDO
    _weight_function: Callable[[float], float] = weighting_function(
        60, 100, 14 * 24 * 60 * 60, 0.01
    )

    _questions: set[str]

    def __init__(self, config: ConfigDataDO):
        self._config = config

        self._score_history = config.load_history()

        self._questions = set()

        self._load_questions()

    @property
    def config(self):
        return self._config

    def _load_questions(self):
        """Loads questions from the questions file."""
        for sentence in self.config.load_questions():
            if sentence not in self._questions:
                self._questions.add(sentence)

    @property
    def _all_sentence_scores(self) -> dict[str, list[ScoreDO]]:
        # Returns all the scores for all the sentences
        ans = {}
        for sentence in self._questions:
            ans[sentence] = self._score_history.scores_by_sentence(sentence)

        return ans

    def sentence_score(self, sentence: str) -> float:
        """Returns the score of a sentence."""
        scores = [
            score
            for score in self._score_history.scores_by_sentence(sentence)
            if score.timestamp - datetime.datetime.now() < datetime.timedelta(days=14)
        ]  # We only care for the last 14 days
        # exponential-weights. We want to give more weight to the most recent scores, and have a exponential decay for the older ones as a function of time delta to now.
        # We will use decay factor such that the weight for a sentece done 1 minute ago is 100, and weight of sentence done 14 days ago is 0.01.
        if len(scores) == 0:
            return 0.0

        weights = [
            self._weight_function(
                max(
                    datetime.timedelta(minutes=1).seconds,
                    (datetime.datetime.now() - score.timestamp).seconds,
                )
            )
            for score in scores
        ]

        return sum(
            [score.overall_score * weight for score, weight in zip(scores, weights)]
        ) / sum(weights)

    def sentence_scores(self) -> list[tuple[float, str]]:
        """Returns a list of tuples with the sentence and its score. The list is sorted by score."""
        scores = [
            (self.sentence_score(sentence), sentence) for sentence in self._questions
        ]
        return sorted(scores)

    @overrides
    def get_next_sentence(self) -> str:
        """Returns the sentence that the user should be asked next."""
        return self.sentence_scores()[0][1]

    @overrides
    def set_sentence_answer(
            self,
            sentence: str,
            user_answer: str,
            thinking_time: float,
            speaking_time: float,
            saved_audio_path: Path,
    ) -> ScoreDO:
        """Sets the answer of a sentence."""
        assert sentence in self._questions, f"Unknown sentence: {sentence}"

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
