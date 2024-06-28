import difflib
import json
import heapq
import os
from dataclasses import dataclass
from pathlib import Path
import datetime
import importlib.resources

import numpy as np
from .voice_sample import VoiceSample


@dataclass
class TotalScore:
    accuracy: float = 0.0
    speed: float = 0.0
    correct: float = 0.0
    incorrect: float = 0.0
    total_questions: float = 0.0

    @staticmethod
    def FromDict(d: dict):
        return TotalScore(
            d["accuracy"],
            d["speed"],
            d["correct"],
            d["incorrect"],
            d["total_questions"],
        )

    def dict(self):
        return {
            "accuracy": self.accuracy,
            "speed": self.speed,
            "correct": self.correct,
            "incorrect": self.incorrect,
            "total_questions": self.total_questions,
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


# def check_directories():
#     Path(os.path.join(os.getcwd(), "data/audio/user")).mkdir(
#         parents=True, exist_ok=True
#     )


def get_resource_path(audio_file: Path | str) -> Path:
    return importlib.resources.files("loudreadingskill") / audio_file


class Scoring:
    _answers: dict[str, Score]
    _answers_file: Path
    _scores_sort: list[(Score, str)]
    _total_score: TotalScore
    _total_scores_file: Path
    _scoring_settings: dict[str, float]

    def __init__(
        self,
        questions_file: Path = "data/sentences.txt",
        answers_file: Path = "data/answers.json",
        total_scores_file: Path = "data/scores.json",
        settings_file: Path = "data/settings.json",
    ):
        self._answers_file = answers_file
        self._total_scores_file = total_scores_file
        self._answers = {}
        self._scores_sort = []
        self._recordings = {}
        self._total_score = TotalScore()

        self.load_answers()
        self.load_questions(questions_file)
        self.load_total_scores()
        self.load_settings(settings_file)
        heapq.heapify(self._scores_sort)

    def load_answers(self):
        self._answers = {
            sentence: Score.FromDict(score)
            for sentence, score in create_and_load_file(self._answers_file, {}).items()
        }
        self._scores_sort = [
            (score, sentence) for sentence, score in self._answers.items()
        ]

    def load_questions(self, questions_file: Path):
        for line in open(questions_file):
            sentence = line.strip()
            if sentence not in self._answers:
                self._answers[sentence] = Score()
                self._scores_sort.append((Score(), sentence))

    def load_total_scores(self):
        self._total_score = TotalScore.FromDict(
            create_and_load_file(self._total_scores_file, self._total_score.dict())
        )

    def load_settings(self, settings_file: Path):
        pass

    def get_next_sentence(self) -> str:
        return heapq.heappop(self._scores_sort)[1]

    def set_sentence_answer(
        self, sentence: str, user_answer: str, accuracy_score: float, time_score: float
    ):
        score = Score(accuracy_score, time_score, user_answer, datetime.datetime.now())
        self._answers[sentence] = score
        heapq.heappush(self._scores_sort, (score, sentence))
        with open(self._answers_file, "w") as fw:
            jsonobj = json.dumps(
                {sentence: score.dict() for sentence, score in self._answers.items()},
                indent=4,
            )
            fw.write(jsonobj)

    def save_user_audio(self, audio: VoiceSample):
        file = Path(
            f"data/audio/user/{datetime.datetime.now().isoformat(sep='-', timespec='seconds')}.wav"
        )
        open(os.path.join(os.getcwd(), str(file)), "w").close()
        audio.save(file)

    def total_scores(self) -> TotalScore:
        return self._total_score

    def update_total_scores(self, accuracy: float, speed: float) -> bool:
        self._total_score.accuracy += accuracy
        self._total_score.accuracy = np.round(self._total_score.accuracy, 2)
        self._total_score.speed += speed
        self._total_score.speed = np.round(self._total_score.speed, 2)
        if accuracy == 1.0 and speed == 1.0:  # TODO get correct condition from settings
            self._total_score.correct += 1
            correct = True
        else:
            self._total_score.incorrect += 1
            correct = False
        self._total_score.total_questions += 1
        with open(self._total_scores_file, "w") as fw:
            jsonobj = json.dumps(self._total_score.dict(), indent=4)
            fw.write(jsonobj)
        return correct


def create_and_load_file(file_name: Path, default_content):
    try:
        with open(file_name, "r") as fr:
            try:
                return json.load(fr)
            except json.JSONDecodeError:
                with open(file_name, "w") as fw:
                    jsonobj = json.dumps(default_content, indent=4)
                    fw.write(jsonobj)
    except FileNotFoundError:
        with open(file_name, "w") as fw:
            jsonobj = json.dumps(default_content, indent=4)
            fw.write(jsonobj)
    return default_content


def just_letters(s: str) -> str:
    return " ".join(s.lower().translate(str.maketrans("", "", "!?.,;:-")).split())


def calculate_timeout_from_sentence(sentence: str) -> float:
    return len(just_letters(sentence)) / 5 + 4


def calc_time_penalty(time_taken, sentence: str) -> float:
    timeout = calculate_timeout_from_sentence(sentence)

    if time_taken < timeout * 2 and not time_taken < timeout:
        return 0.5
    if time_taken < timeout:
        return 1
    return 0


def score_sentence(correct_sentence: str, user_sentence: str) -> tuple[float, str]:
    sequence_matcher = difflib.SequenceMatcher(
        None, just_letters(correct_sentence), just_letters(user_sentence)
    )
    # Calculate number of words that were read wrong.
    # 1. Calculate positions of spaces in the correct sentence
    correct_spaces = [-1] + [i for i, c in enumerate(correct_sentence) if c == " "]
    correct_spaces.append(len(correct_sentence))
    # Find what words were read wrong
    wrong_words = 0
    mb = sequence_matcher.get_matching_blocks()
    mb = [mb for mb in mb if mb.size > 0]
    if len(mb) == 0:
        return 0, highlight_sentence(
            correct_sentence, [False] * (len(correct_spaces) - 1)
        )

    left_word_pos_idx = 0
    sequence_pos = 0
    words = [True] * (
        len(correct_spaces) - 1
    )  # Each word will get a True if was correctly read, or False if not

    correct_pos_left = mb[sequence_pos].a
    correct_pos_right = mb[sequence_pos].size
    # All the words before the first match are wrong.
    while correct_spaces[left_word_pos_idx] + 1 < correct_pos_left:
        words[left_word_pos_idx] = False
        left_word_pos_idx += 1
        if left_word_pos_idx == len(correct_spaces) - 1:
            return 0, highlight_sentence(correct_sentence, words)

    while True:  # Driven by correct_pos.
        correct_pos_left = mb[sequence_pos].a
        correct_pos_right = mb[sequence_pos].size + mb[sequence_pos].a

        while True:
            left_word_pos = correct_spaces[left_word_pos_idx]
            right_word_pos = correct_spaces[left_word_pos_idx + 1]
            if right_word_pos < correct_pos_right:
                left_word_pos_idx += 1
                if left_word_pos_idx == len(correct_spaces) - 1:
                    break
                continue
            break
        if left_word_pos_idx == len(correct_spaces) - 1:
            break

        sequence_pos += 1
        if sequence_pos == len(mb):
            # We are going to exit. All the words not read are wrong (missing).
            left_word_pos_idx += 1
            while left_word_pos_idx < len(correct_spaces) - 1:
                words[left_word_pos_idx] = False
                left_word_pos_idx += 1
            break
        correct_pos_left = mb[sequence_pos].a
        correct_pos_right = mb[sequence_pos].size + mb[sequence_pos].a
        while left_word_pos < correct_pos_left:
            words[left_word_pos_idx] = False
            left_word_pos_idx += 1
            if left_word_pos_idx == len(correct_spaces) - 1:
                break
            left_word_pos = correct_spaces[left_word_pos_idx]
            right_word_pos = correct_spaces[left_word_pos_idx + 1]
        if left_word_pos_idx == len(correct_spaces) - 1:
            break

    total_word_count = len(correct_spaces) - 1
    wrong_words = sum(1 for word in words if not word)
    accuracy = (total_word_count - wrong_words) / total_word_count
    accuracy = np.round(accuracy, 2)
    return accuracy, highlight_sentence(correct_sentence, words)


def highlight_sentence(correct_sentence: str, words: list[bool]) -> str:
    reference_tokens = correct_sentence.split()
    formatted_text = ""
    for i, token in enumerate(reference_tokens):
        if words[i]:
            formatted_text += token + " "
        else:
            formatted_text += f"<span style='background-color: #FF0000'>{token}</span> "
    return formatted_text
