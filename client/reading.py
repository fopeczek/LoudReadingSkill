import datetime
import time
import tkinter as tk
from pathlib import Path
from threading import Thread
from pydantic import BaseModel

import numpy as np
from pydub import AudioSegment
from pydub.playback import play
import argparse

from core import (
    get_resource_path,
    ConfigDataDO,
    IScoring,
    load_config,
    Scoring_Arcade,
    Scoring_Story,
    TotalScoreDO,
    ScoreDO,
    VoiceSample,
    just_letters_mapping,
)
from .recorder import Recorder
from .speech2text import Speech2Text


def highlight_sentence(correct_sentence: str, words: list[bool]) -> str:
    char_ranges = just_letters_mapping(correct_sentence)
    formatted_text = ""
    last_end = 0
    for i, (start, end) in enumerate(char_ranges):
        formatted_text += correct_sentence[last_end:start]

        token = correct_sentence[start:end]
        if words[i]:
            formatted_text += token
        else:
            formatted_text += f"*{token}*"

        last_end = end
        if i == len(char_ranges) - 1:
            formatted_text += correct_sentence[end:]
    return formatted_text


class Answer(BaseModel):
    question: str
    answer: str
    accuracy: float
    recording: VoiceSample


class ReadingApp:
    _scoring: IScoring
    _total_score: TotalScoreDO
    _recorder: Recorder
    _speech2text: Speech2Text
    _config: ConfigDataDO

    started_recording: bool
    rerolled: int

    current_sentence: str
    answers: list[Answer]
    current_answer: int
    _last_score: ScoreDO

    time_start: float
    time_taken: float

    connection_error_popup: bool

    _window: tk.Tk
    _question_text: tk.Text
    _record_button: tk.Button
    _next_question_button: tk.Button
    _accuracy_score_label: tk.Label
    _total_questions_label: tk.Label

    def __init__(self, config: ConfigDataDO):
        self._config = config

        self._total_score = config.load_total_scores()

        if config.story_mode:
            self._scoring = Scoring_Story(config)
            self._scoring.set_next_sentence(self._total_score.story_index)
        else:
            self._scoring = Scoring_Arcade(config)

        self._recorder = Recorder()

        self.started_recording = False
        self.rerolled = 0

        self.current_sentence = ""
        self.answers = []
        self.current_answer = 0

        self.time_start = 0.0
        self.time_taken = 0.0
        self._last_score = ScoreDO()

        self.connection_error_popup = False

        self._speech2text = Speech2Text(
            server_url=config.whisper_host,
            run_locally=config.run_whisper_locally,
        )

        self._user_answer = None
        self._replay_last_button = None
        self._info_label = None
        self._previous_answer = None
        self._next_answer = None

        self._window = tk.Tk()
        self._window.geometry("800x250")
        self._window.resizable(False, False)
        self._window.attributes("-type", "dialog")
        self._window.title("Reading")
        self._window.configure(bg="black")
        self._window.grid_columnconfigure(0, weight=1)
        self._window.grid_columnconfigure(1, weight=1)

        self._question_text = tk.Text(
            self._window, height=1, width=80, wrap="word", font=("Helvetica", 32)
        )
        self._question_text.configure(background="black", foreground="white")
        self._question_text.tag_configure("center", justify="center")
        self._question_text.tag_config("highlight", justify="center", foreground="red")
        self._question_text.grid(row=0, column=0, columnspan=3, pady=20)

        self._record_button = tk.Button(self._window, text="Start recording")
        self._record_button.configure(background="black", foreground="white")
        self._record_button.configure(
            activebackground="black", activeforeground="white"
        )
        self._record_button.bind("<ButtonPress>", self.toggle_recording)
        self._window.bind("<KeyPress>", self.toggle_recording)
        self._record_button.grid(row=1, column=0, columnspan=3)

        self._next_question_button = tk.Button(self._window, text="Next question")
        self._next_question_button.configure(background="black", foreground="white")
        self._next_question_button.configure(
            activebackground="black", activeforeground="white"
        )
        self._next_question_button.bind("<ButtonPress>", self.next_question)
        self._next_question_button.grid(row=2, column=0, columnspan=3, pady=5)

        self._accuracy_score_label = tk.Label(
            self._window, text=f"Accuracy: {self._total_score.accuracy}"
        )
        self._accuracy_score_label.configure(background="black", foreground="white")
        self._accuracy_score_label.grid(row=3, column=0, columnspan=3)

        self._total_questions_label = tk.Label(
            self._window,
            text=f"Total questions: {self._total_score.total_questions}",
        )
        self._total_questions_label.configure(background="black", foreground="white")
        self._total_questions_label.grid(row=6, column=0, columnspan=3)

        self.next_question()

        self.check_speech2text()

    def toggle_recording(self, event):
        if (
            event.keysym == "space" or event.widget == self._record_button
        ) and not self.connection_error_popup:
            if not self.started_recording:
                if (
                    len(self.answers) < self._config.max_answers_per_question
                    or self._config.story_mode
                ):
                    self.start_recording()
            else:
                self.stop_recording()

    def start_recording(self):
        self._last_score = ScoreDO()
        self.time_taken = time.time() - self.time_start
        self.update_scores()
        song = AudioSegment.from_mp3(get_resource_path("start.mp3"))
        Thread(target=play, args=(song,)).start()
        self._recorder.start_recording()
        self.started_recording = True
        self._record_button["state"] = "active"
        self._record_button["text"] = "Stop recording"
        self._record_button["background"] = "gray"
        self._record_button["activebackground"] = "gray"
        self._info_label.destroy() if self._info_label is not None else None

    def stop_recording(self):
        self._recorder.stop_recording()
        song = AudioSegment.from_mp3(get_resource_path("end.mp3"))
        Thread(target=play, args=(song,)).start()
        self.started_recording = False
        self._record_button["text"] = "Start recording"
        self._record_button["background"] = "black"
        self._record_button["activebackground"] = "black"
        self.process_last_recording()

    def process_last_recording(self):
        loading = self.loading_popup("Processing", "Processing... ")
        sound = self._recorder.get_last_recording()
        if sound.length() < 1.0:  # TODO add check for too quiet and too loud
            loading.destroy()
            self._info_label = tk.Label(self._window, text="Recording too short. ")
            self._info_label.configure(background="black", foreground="red")
            self._info_label.grid(row=1, column=2, padx=20)
            # TODO replace with place or pack, rare case if answered 2 times and on 3rd time recording is too short
            return
        success, transcript = self._speech2text.get_transcript(sound)
        loading.destroy()

        if not success:
            self.no_connection_popup()
            return

        self.process_user_answer(transcript)

    def process_user_answer(self, transcript):
        if not transcript or len(transcript) < 1 or transcript == '""':
            self._info_label = tk.Label(
                self._window, text="Could not recognize. Try again"
            )
            self._info_label.configure(background="black", foreground="red")
            self._info_label.grid(row=1, column=2, padx=20)
            # TODO replace with place or pack, rare case if answered 2 times and on 3rd time recording is too short
            return

        self.answers.append(
            Answer(
                question=self.current_sentence,
                answer=transcript,
                accuracy=0,
                recording=self._recorder.get_last_recording(),
            )
        )
        self.current_answer = len(self.answers) - 1

        self._record_button["text"] = "Start recording"
        self._next_question_button["state"] = "normal"

        if len(self.answers) == 1:
            self.rerolled = 0
            self.setup_user_answer(transcript)
            self.setup_replay_button()

        if len(self.answers) == 2:
            self.setup_multiple_answers_ui()

        self.update_window_size()
        self.check_answer(transcript)

    def check_answer(self, transcript: str):
        self._config.recordings_directory.mkdir(parents=True, exist_ok=True)
        saved_audio_file = (
            self._config.recordings_directory
            / f"{datetime.datetime.now().isoformat(sep='-', timespec='seconds')}.wav"
        )
        last_audio = self._recorder.get_last_recording()
        last_audio.save(saved_audio_file)

        score: ScoreDO = self._scoring.set_sentence_answer(
            sentence=self.current_sentence,
            user_answer=transcript,
            thinking_time=self.time_taken,
            speaking_time=last_audio.length(),
            saved_audio_path=saved_audio_file,
        )
        self._last_score = score
        self.update_scores(True)
        redacted_answer_in_html = highlight_sentence(self.current_sentence, score.words)
        self.answers[-1].accuracy = score.accuracy
        self.answers[-1].question = redacted_answer_in_html

        if self._config.story_mode:
            if score.accuracy < self._config.incorrect_overall_score_threshold:
                song = AudioSegment.from_mp3(get_resource_path("incorrect.mp3"))
                Thread(target=play, args=(song,)).start()

                self._next_question_button["state"] = "disabled"
            else:
                self._next_question_button["state"] = "normal"
            if score.accuracy == 1.0:
                song = AudioSegment.from_mp3(get_resource_path("correct.mp3"))
                Thread(target=play, args=(song,)).start()

                self._record_button["state"] = "disabled"
            else:
                self._record_button["state"] = "normal"
        else:
            if len(self.answers) < self._config.max_answers_per_question:
                self._record_button["state"] = "normal"
            else:
                self._record_button["state"] = "disabled"
            self._next_question_button["state"] = "normal"
            if score.accuracy < self._config.incorrect_overall_score_threshold:
                song = AudioSegment.from_mp3(get_resource_path("incorrect.mp3"))
                Thread(target=play, args=(song,)).start()
            if score.accuracy > self._config.correct_overall_score_threshold:
                song = AudioSegment.from_mp3(get_resource_path("correct.mp3"))
                Thread(target=play, args=(song,)).start()

        self.update_user_answer()

    def setup_user_answer(self, transcript):
        self._user_answer = tk.Text(self._window, height=np.ceil(len(transcript) / 80))
        self._user_answer.configure(background="black", foreground="white")
        self._user_answer.delete("1.0", tk.END)
        self._user_answer.insert(tk.END, transcript, "center")
        self._user_answer.tag_configure("center", justify="center")
        self._user_answer.grid(row=7, column=0, columnspan=3, pady=10)

    def setup_replay_button(self):
        self._replay_last_button = tk.Button(self._window, text="Replay last recording")
        self._replay_last_button.configure(background="black", foreground="white")
        self._replay_last_button.configure(
            activebackground="black", activeforeground="white"
        )
        self._replay_last_button.bind("<ButtonPress>", self.replay_answer)
        self._replay_last_button.grid(row=8, column=0, columnspan=3)

    def setup_multiple_answers_ui(self):
        self._previous_answer = tk.Button(self._window, text="<")
        self._previous_answer.configure(background="black", foreground="white")
        self._previous_answer.configure(
            activebackground="black", activeforeground="white"
        )
        self._previous_answer.bind("<ButtonPress>", self.previous_answer)
        self._previous_answer.grid(row=8, column=0, columnspan=1)

        self._next_answer = tk.Button(self._window, text=">")
        self._next_answer.configure(background="black", foreground="white")
        self._next_answer.configure(activebackground="black", activeforeground="white")
        self._next_answer.bind("<ButtonPress>", self.next_answer)
        self._next_answer.grid(row=8, column=1, columnspan=3)
        self._next_answer["state"] = "disabled"

    def previous_answer(self, event):
        self.current_answer -= 1
        self._next_answer["state"] = "normal"
        if self.current_answer <= 0:
            self.current_answer = 0
            self._previous_answer["state"] = "disabled"
        self.update_user_answer()

    def next_answer(self, event):
        self.current_answer += 1
        self._previous_answer["state"] = "normal"
        if self.current_answer >= len(self.answers) - 1:
            self.current_answer = len(self.answers) - 1
            self._next_answer["state"] = "disabled"
        self.update_user_answer()

    def update_user_answer(self):
        self._question_text.delete("1.0", tk.END)
        self.insert_colored_text(self.answers[self.current_answer].question)
        self._user_answer.delete("1.0", tk.END)
        self._user_answer.insert(
            tk.END, self.answers[self.current_answer].answer, "center"
        )
        self._user_answer.height = np.ceil(
            len(self.answers[self.current_answer].answer) / 80
        )
        self.update_scores(True)
        self.update_window_size()

    def update_scores(self, show_delta=False):
        self._accuracy_score_label["text"] = (
            f"Accuracy: {np.round(self._total_score.accuracy, 2)}"
        )
        self._total_questions_label["text"] = (
            f"Total questions: {self._total_score.total_questions}"
        )
        if show_delta:
            self._accuracy_score_label["text"] += (
                f" + {np.round(self._last_score.accuracy, 2)}"
            )
            self._total_questions_label["text"] += " + 1"

    def replay_answer(self, event):
        song = self.answers[self.current_answer].recording
        Thread(target=song.play).start()

    def insert_colored_text(self, html_text):
        import re

        pattern = re.compile(r"\*(.*?)\*")
        last_end = 0
        self._question_text.config(state="normal")
        self._question_text.delete("1.0", tk.END)
        for match in pattern.finditer(html_text):
            self._question_text.insert(tk.END, html_text[last_end : match.start()])
            self._question_text.insert(tk.END, match.group(1), "highlight")
            last_end = match.end()
        self._question_text.insert(tk.END, html_text[last_end:], "center")
        self._question_text.config(state="disabled")

    def next_question(self, event=None):
        if self._next_question_button.config("state")[-1] == "disabled":
            return
        self._total_score.add_score(self._last_score)
        self._last_score = ScoreDO()
        if self.rerolled < self._config.max_new_question_rolls:
            self.current_sentence = self._scoring.get_next_sentence()
            self._question_text["height"] = np.ceil(len(self.current_sentence) / 80)
            self.insert_colored_text(self.current_sentence)
            if self._user_answer is not None:
                self._user_answer.destroy()
                self._user_answer = None
            if self._replay_last_button is not None:
                self._replay_last_button.destroy()
                self._replay_last_button = None
            if self._info_label is not None:
                self._info_label.destroy()
                self._info_label = None
            if self._previous_answer is not None:
                self._previous_answer.destroy()
                self._previous_answer = None
            if self._next_answer is not None:
                self._next_answer.destroy()
                self._next_answer = None
            self.time_start = time.time()

            self.answers = []
            self.started_recording = False
            self.rerolled += 1
            self._record_button["state"] = "normal"
            self._next_question_button["state"] = "disabled"
            self.update_window_size()
            self.update_scores()

    def update_window_size(self):
        lines = np.ceil(len(self.current_sentence) / 80)
        if self._user_answer is not None:
            lines += np.ceil(len(self._user_answer.get("1.0", tk.END)) / 80)
        if len(self.answers) > 0:
            lines += 2
        self._window.geometry(f"800x{int(250 + 20 * lines)}")

    def check_speech2text(self):
        if not self._speech2text.check():
            Thread(target=self.no_connection_popup, args=(False,)).start()
            return

    def no_connection_popup(self, process_last_recording=True):
        self.connection_error_popup = True
        self._record_button["state"] = "disabled"
        self._next_question_button["state"] = "disabled"
        popup = tk.Toplevel(self._window)
        popup.title("Error")
        popup.geometry("300x100")
        popup.resizable(False, False)
        popup.attributes("-type", "dialog")
        popup.attributes("-topmost", True)
        popup.configure(bg="black")
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=1)
        label = tk.Label(
            popup,
            text="Could not connect to the server. ",
            background="black",
            foreground="white",
        )
        label.grid(row=0, column=0, columnspan=2, pady=15)
        button_run_locally = tk.Button(
            popup,
            text="Run locally",
            command=lambda: self.run_locally(popup, process_last_recording),
        )
        button_run_locally.configure(background="black", foreground="white")
        button_run_locally.grid(row=1, column=0)
        try:
            import whisper  # noqa F401
        except ImportError:
            button_run_locally["state"] = "disabled"
        button_exit = tk.Button(
            popup, text="Ok", command=lambda: self.close_connection_error_popup(popup)
        )
        button_exit.configure(background="black", foreground="white")
        button_exit.grid(row=1, column=1)
        popup.lift()

    def close_connection_error_popup(self, popup):
        self.connection_error_popup = False
        if len(self.answers) < self._config.max_answers_per_question:
            self._record_button["state"] = "normal"
        if self.rerolled < self._config.max_new_question_rolls:
            self._next_question_button["state"] = "normal"
        popup.destroy()

    def run_locally(self, popup, process_last_recording):
        loading = self.loading_popup("Loading", "Loading... ")
        self._config.run_whisper_locally = True
        self._config.save_config()
        self._speech2text.__init__(
            server_url=self._config.whisper_host,
            run_locally=self._config.run_whisper_locally,
        )
        self.time_start = time.time()
        loading.destroy()
        self.close_connection_error_popup(popup)
        if process_last_recording:
            self.process_last_recording()

    def loading_popup(self, title, text):
        popup = tk.Toplevel(self._window)
        popup.title(title)
        popup.geometry("150x50")
        popup.resizable(False, False)
        popup.attributes("-type", "dialog")
        popup.attributes("-topmost", True)
        popup.configure(bg="black")
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(0, weight=1)
        label = tk.Label(popup, text=text, background="black", foreground="white")
        label.grid(row=0, column=0)
        return popup

    @property
    def window(self):
        return self._window


def main(config_path: Path = None):
    if config_path is None:
        config_path = Path("config.json")
    parser = argparse.ArgumentParser(description="Reading App")
    parser.add_argument(
        "--sentences",
        type=str,
        default=None,
        help="Path to sentences.txt",
    )
    parser.add_argument("--whisper-server", type=str, default="192.168.42.5:8000")
    parser.add_argument("--config-path", type=str, default=None)
    args = parser.parse_args()

    if args.config_path is None:
        args.config_path = Path("config.json")
    if not args.config_path.exists():
        config = ConfigDataDO()
    else:
        config = load_config(config_path)

    # Now you can access the sentences file path with args.sentences
    if args.sentences is not None:
        sentences_file_path = Path(args.sentences)
        if not sentences_file_path.exists():
            print(f"File {sentences_file_path} does not exist. ")
        config.questions_file = sentences_file_path

    if args.whisper_server is not None:
        config.whisper_host = args.whisper_server
        config.run_whisper_locally = False

    app = ReadingApp(config)
    try:
        app.window.mainloop()
    finally:
        app._config.save(config_path)
