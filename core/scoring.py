import difflib
import json
import heapq
import os
from dataclasses import dataclass
from pathlib import Path
import datetime

import numpy as np
from core import create_and_load_file, just_letters, VoiceSample, Config


@dataclass
class TotalScore:
    accuracy: float = 0.0
    speed: float = 0.0
    correct: float = 0.0
    incorrect: float = 0.0
    total_questions: float = 0.0
    story_index: int = 0

    @staticmethod
    def FromDict(d: dict):
        return TotalScore(
            d["accuracy"],
            d["speed"],
            d["correct"],
            d["incorrect"],
            d["total_questions"],
            d["story_index"],
        )

    def dict(self):
        return {
            "accuracy": self.accuracy,
            "speed": self.speed,
            "correct": self.correct,
            "incorrect": self.incorrect,
            "total_questions": self.total_questions,
            "story_index": self.story_index,
        }


@dataclass(order=True)
class Score:
    accuracy: float = 0.0
    time: float = 0.0
    user_answer: str = ""
    timestamp: datetime.datetime = datetime.datetime.now()

    @staticmethod
    def FromDict(d: dict):
        return Score(
            d["accuracy"],
            d["time"],
            d["user_answer"],
            datetime.datetime.fromisoformat(d["timestamp"]),
        )

    def dict(self):
        return {
            "accuracy": self.accuracy,
            "time": self.time,
            "user_answer": self.user_answer,
            "timestamp": self.timestamp.isoformat(),
        }


def check_directories():
    Path(os.path.join(os.getcwd(), "data/audio/user")).mkdir(
        parents=True, exist_ok=True
    )


def get_resource_path(audio_file: Path | str) -> Path:
    current_file_path = Path(__file__)
    project_root = current_file_path.parent.parent
    return project_root / "data" / "audio" / audio_file
    # return files("data.audio") / audio_file


class Scoring:
    _answers: dict[str, Score]
    _scores_sort: list[(Score, str)]
    _total_score: TotalScore
    _config: Config

    def __init__(
        self,
        config: Config,
    ):
        self._config = config
        self._answers = {}
        self._scores_sort = []
        self._total_score = TotalScore()

        check_directories()

        self.load_answers()
        self.load_questions()
        self.load_total_scores()
        heapq.heapify(self._scores_sort)

    def load_answers(self):
        self._answers = {
            sentence: Score.FromDict(score)
            for sentence, score in create_and_load_file(
                self._config.get_config().answers_file, {}
            ).items()
        }
        self._scores_sort = [
            (score, sentence) for sentence, score in self._answers.items()
        ]

    def load_questions(self):
        for line in open(self._config.get_config().questions_file, "r"):
            sentence = line.strip()
            if sentence not in self._answers:
                self._answers[sentence] = Score()
                self._scores_sort.append((Score(), sentence))

    def load_total_scores(self):
        self._total_score = TotalScore.FromDict(
            create_and_load_file(
                self._config.get_config().scores_file, self._total_score.dict()
            )
        )

    def get_next_sentence(self) -> str:
        if self._config.get_config().story_mode:
            out = list(self._answers)[self._total_score.story_index]
            return out
        else:
            return heapq.heappop(self._scores_sort)[1]

    def set_sentence_answer(
        self, sentence: str, user_answer: str, accuracy_score: float, time_score: float
    ):
        score = Score(accuracy_score, time_score, user_answer, datetime.datetime.now())
        self._answers[sentence] = score
        heapq.heappush(self._scores_sort, (score, sentence))
        with open(self._config.get_config().answers_file, "w") as fw:
            jsonobj = json.dumps(
                {sentence: score.dict() for sentence, score in self._answers.items()},
                indent=4,
            )
            fw.write(jsonobj)

    def save_user_audio(self, audio: VoiceSample):
        file = Path(
            f"{self._config.get_config().recordings_directory}/"
            f"{datetime.datetime.now().isoformat(sep='-', timespec='seconds')}.wav"
        )
        open(os.path.join(os.getcwd(), str(file)), "w").close()
        audio.save(file)

    def total_scores(self) -> TotalScore:
        return self._total_score

    def update_total_scores(self, accuracy: float, speed: float) -> tuple[bool, bool]:
        self._total_score.accuracy += accuracy
        self._total_score.accuracy = np.round(self._total_score.accuracy, 2)
        self._total_score.speed += speed
        self._total_score.speed = np.round(self._total_score.speed, 2)
        correct = False
        incorrect = False
        if (
            accuracy >= self._config.get_config().correct_min_accuracy
            and speed >= self._config.get_config().correct_min_speed
        ):
            self._total_score.correct += 1
            self._total_score.story_index += 1
            correct = True
        elif (
            accuracy < self._config.get_config().incorrect_max_accuracy
            or speed < self._config.get_config().incorrect_max_speed
        ):
            self._total_score.incorrect += 1
            incorrect = True
        self._total_score.total_questions += 1
        with open(self._config.get_config().scores_file, "w") as fw:
            jsonobj = json.dumps(self._total_score.dict(), indent=4)
            fw.write(jsonobj)
        return correct, incorrect


def calculate_timeout_from_sentence(sentence: str) -> float:
    return len(just_letters(sentence)) / 6 + 4


def calc_time_penalty(time_taken, sentence: str) -> float:
    timeout = calculate_timeout_from_sentence(sentence)

    if time_taken < timeout * 2 and not time_taken < timeout:
        return 0.5
    if time_taken < timeout:
        return 1
    return 0


def score_internal(correct_tokens: list[str], user_tokens: list[str]) -> list[bool]:
    sequence_matcher = difflib.SequenceMatcher(
        None, "".join(correct_tokens), "".join(user_tokens)
    )
    mb = sequence_matcher.get_matching_blocks()
    mb = [mb for mb in mb if mb.size > 0]
    if len(mb) == 0:
        return [False] * len(correct_tokens)

    left_word_pos_idx = 0
    sequence_pos = 0
    words = [True] * (
        len(correct_tokens)
    )  # Each word will get a True if was correctly read, or False if not

    # token[i] == "".join(correct_tokens[:i])[token_breaks[i]:token_breaks[i+1]]
    token_lengths = [len(token) for token in correct_tokens]
    token_breaks = [sum(token_lengths[:i]) for i in range(0, 1 + len(correct_tokens))]

    correct_pos_left = mb[sequence_pos].a
    correct_pos_right = mb[sequence_pos].size

    # All the words before the first match are wrong.
    while token_breaks[left_word_pos_idx] + 1 < correct_pos_left:
        words[left_word_pos_idx] = False
        left_word_pos_idx += 1
        if left_word_pos_idx == len(token_breaks) - 1:
            return words

    while True:  # Driven by correct_pos.
        correct_pos_left = mb[sequence_pos].a
        correct_pos_right = mb[sequence_pos].size + mb[sequence_pos].a

        while True:
            left_word_pos = token_breaks[left_word_pos_idx]
            right_word_pos = token_breaks[left_word_pos_idx + 1]
            if right_word_pos <= correct_pos_right:
                left_word_pos_idx += 1
                if left_word_pos_idx == len(token_breaks) - 1:
                    break
                continue
            break
        if left_word_pos_idx == len(token_breaks) - 1:
            break

        sequence_pos += 1
        if sequence_pos == len(mb):
            # We are going to exit. All the words not read are wrong (missing).
            left_word_pos_idx += 1
            while left_word_pos_idx < len(token_breaks) - 1:
                words[left_word_pos_idx] = False
                left_word_pos_idx += 1
            break
        correct_pos_left = mb[sequence_pos].a
        correct_pos_right = mb[sequence_pos].size + mb[sequence_pos].a
        while left_word_pos <= correct_pos_left:
            words[left_word_pos_idx] = False
            left_word_pos_idx += 1
            if left_word_pos_idx == len(token_breaks) - 1:
                break
            left_word_pos = token_breaks[left_word_pos_idx]
            right_word_pos = token_breaks[left_word_pos_idx + 1]
        if left_word_pos_idx == len(token_breaks) - 1:
            break

    return words


def add_space_tokens(tokens: list[str]) -> list[str]:
    # Adds space token ([" "]) between each token, so "".join(correct_sentence_spaces) = correct_sentence_letters
    token_spaces = []
    for token in tokens:
        if len(token_spaces) == 0:
            token_spaces.append(token)
        else:
            token_spaces.append(" ")
            token_spaces.append(token)
    return token_spaces


def score_sentence(correct_sentence: str, user_sentence: str) -> tuple[float, str]:
    correct_sentence_letters = just_letters(correct_sentence)
    user_sentence_letters = just_letters(user_sentence)

    correct_tokens = correct_sentence_letters.split()
    user_tokens = user_sentence_letters.split()

    correct_tokens_spaces = add_space_tokens(correct_tokens)
    user_tokens_spaces = add_space_tokens(user_tokens)

    ans = [True for _ in correct_tokens]

    words = score_internal(correct_tokens_spaces, user_tokens_spaces)

    # Each False in space word is propagated as False to the adjoining letter words
    for i in range(len(ans) - 1):
        if not words[2 * i]:
            ans[i] = False
        else:
            if not words[2 * i + 1]:
                ans[i] = False
                ans[i + 1] = False

    if not words[-1]:
        ans[-1] = False

    total_word_count = len(correct_tokens)
    wrong_words = sum(1 for word in ans if not word)
    accuracy = (total_word_count - wrong_words) / total_word_count
    # accuracy = np.round(accuracy, 2)
    return accuracy, highlight_sentence(correct_sentence, ans)


def highlight_sentence(correct_sentence: str, words: list[bool]) -> str:
    reference_tokens = correct_sentence.split()
    formatted_text = ""
    for i, token in enumerate(reference_tokens):
        if words[i]:
            formatted_text += token + " "
        else:
            formatted_text += f"<span style='background-color: #FF0000'>{token}</span> "
    return formatted_text
