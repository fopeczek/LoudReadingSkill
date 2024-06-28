import numpy as np
import os
import time
import tkinter as tk
from pydub import AudioSegment
from pydub.playback import play
from pathlib import Path
from threading import Thread
import argparse

from core import Scoring, score_sentence, calc_time_penalty
from .recorder import Recorder
from .speech2text import Speech2Text


class ReadingApp:
    _scoring: Scoring
    _recorder: Recorder
    _speech2text: Speech2Text

    _window: tk.Tk
    _question_text: tk.Text
    _record_button: tk.Button
    _next_question_button: tk.Button
    _accuracy_score_label: tk.Label
    _total_questions_label: tk.Label
    _time_score_label: tk.Label
    _incorrect_label: tk.Label
    _correct_label: tk.Label

    def __init__(self, sentences_file_path: Path):
        self.started_recording = False
        self.answered_times = 0
        self.max_answers = 1  # TODO get from settings
        self.rerolled = 0
        self.max_rerolls = 1  # TODO get from settings

        self.current_sentence = None
        self.time_start = 0.0
        self.time_taken = 0.0

        self.connection_error_popup = False

        self._scoring = Scoring(questions_file=sentences_file_path)
        self._recorder = Recorder()

        self._speech2text = Speech2Text(run_locally=False)  # TODO get from settings

        self._user_answer = None
        self._info_label = None

        self._window = tk.Tk()
        self._window.geometry("800x250")
        self._window.resizable(False, False)
        self._window.attributes("-type", "dialog")
        self._window.title("Reading")
        self._window.configure(bg="black")
        self._window.grid_columnconfigure(0, weight=1)
        self._window.grid_columnconfigure(1, weight=1)

        self._question_text = tk.Text(self._window, height=1, width=80, wrap="word")
        self._question_text.configure(background="black", foreground="white")
        self._question_text.tag_configure("center", justify="center")
        self._question_text.tag_config("highlight", foreground="red", justify="center")
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
            self._window, text=f"Accuracy: {self._scoring.total_scores().accuracy}"
        )
        self._accuracy_score_label.configure(background="black", foreground="white")
        self._accuracy_score_label.grid(row=3, column=0, columnspan=3)

        self._time_score_label = tk.Label(
            self._window, text=f"Speed: {self._scoring.total_scores().speed}"
        )
        self._time_score_label.configure(background="black", foreground="white")
        self._time_score_label.grid(row=4, column=0, columnspan=3)

        self._correct_label = tk.Label(
            self._window, text=f"Correct: {self._scoring.total_scores().correct}"
        )
        self._correct_label.configure(background="black", foreground="white")
        self._correct_label.grid(row=5, column=0, columnspan=3)

        self._incorrect_label = tk.Label(
            self._window, text=f"Incorrect: {self._scoring.total_scores().incorrect}"
        )
        self._incorrect_label.configure(background="black", foreground="white")
        self._incorrect_label.grid(row=6, column=0, columnspan=3)

        self._total_questions_label = tk.Label(
            self._window,
            text=f"Total questions: {self._scoring.total_scores().total_questions}",
        )
        self._total_questions_label.configure(background="black", foreground="white")
        self._total_questions_label.grid(row=7, column=0, columnspan=3)

        self.next_question()

        self.check_speech2text()

    def toggle_recording(self, event):
        if (
            event.keysym == "space" or event.widget == self._record_button
        ) and not self.connection_error_popup:
            if not self.started_recording:
                if self.answered_times < self.max_answers:
                    self.start_recording()
            else:
                self.stop_recording()

    def start_recording(self):
        self.time_taken = time.time() - self.time_start
        song = AudioSegment.from_mp3(os.path.join(os.getcwd(), "data/audio/start.mp3"))
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
        song = AudioSegment.from_mp3(os.path.join(os.getcwd(), "data/audio/end.mp3"))
        Thread(target=play, args=(song,)).start()
        self.started_recording = False
        self._record_button["text"] = "Start recording"
        self._record_button["background"] = "black"
        self._record_button["activebackground"] = "black"
        self.process_last_recording()

    def process_last_recording(self):
        loading = self.loading_popup("Processing", "Processing... ")
        sound = self._recorder.get_last_recording()
        if sound.length() < 1.0:
            loading.destroy()
            self._info_label = tk.Label(self._window, text="Recording too short. ")
            self._info_label.configure(background="black", foreground="red")
            self._info_label.grid(row=1, column=2, padx=20)
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
            return

        self.answered_times += 1
        self.rerolled = 0
        self._record_button["background"] = "black"
        self._record_button["activebackground"] = "black"
        self._record_button["state"] = "disabled"
        self._record_button["text"] = "Start recording"
        self._next_question_button["state"] = "normal"

        self._user_answer = tk.Text(self._window, height=np.ceil(len(transcript) / 80))
        self._user_answer.configure(background="black", foreground="white")
        self._user_answer.delete("1.0", tk.END)
        self._user_answer.insert(tk.END, transcript, "center")
        self._user_answer.tag_configure("center", justify="center")
        self._user_answer.grid(row=8, column=0, columnspan=2, pady=10)
        self.update_window_size()

        self.check_answer(transcript)

    def insert_colored_text(self, html_text):
        import re

        pattern = re.compile(r"<span style='background-color: #FF0000'>(.*?)</span>")
        last_end = 0
        self._question_text.config(state="normal")
        self._question_text.delete("1.0", tk.END)
        for match in pattern.finditer(html_text):
            self._question_text.insert(tk.END, html_text[last_end : match.start()])
            self._question_text.insert(tk.END, match.group(1), "highlight")
            last_end = match.end()
        self._question_text.insert(tk.END, html_text[last_end:], "center")
        self._question_text.config(state="disabled")

    def check_answer(self, transcript):
        accuracy, redacted_answer_in_html = score_sentence(
            self.current_sentence, transcript
        )
        speed = calc_time_penalty(self.time_taken, self.current_sentence)
        self._accuracy_score_label["text"] += f" + {accuracy}"
        self._time_score_label["text"] += f" + {speed}"

        if self._scoring.update_total_scores(accuracy, speed):
            self._correct_label["text"] += " + 1"
            song = AudioSegment.from_mp3(
                os.path.join(os.getcwd(), "data/audio/correct.mp3")
            )
            Thread(target=play, args=(song,)).start()
        else:
            self._incorrect_label["text"] += " + 1"
            song = AudioSegment.from_mp3(
                os.path.join(os.getcwd(), "data/audio/incorrect.mp3")
            )
            Thread(target=play, args=(song,)).start()
        self._total_questions_label["text"] += " + 1"

        self._scoring.set_sentence_answer(
            self.current_sentence, transcript, accuracy, speed
        )
        self._scoring.save_user_audio(self._recorder.get_last_recording())
        self._question_text.delete("1.0", tk.END)
        self.insert_colored_text(redacted_answer_in_html)

    def next_question(self, event=None):
        if self.rerolled < self.max_rerolls:
            self.current_sentence = self._scoring.get_next_sentence()
            self._question_text["height"] = np.ceil(len(self.current_sentence) / 80)
            self.insert_colored_text(self.current_sentence)
            if self._user_answer is not None:
                self._user_answer.destroy()
                self._user_answer = None
            self.time_start = time.time()
            self.update_window_size()

            self._accuracy_score_label["text"] = (
                f"Accuracy score: {self._scoring.total_scores().accuracy}"
            )
            self._time_score_label["text"] = (
                f"Time score: {self._scoring.total_scores().speed}"
            )
            self._correct_label["text"] = (
                f"Correct: {int(self._scoring.total_scores().correct)}"
            )
            self._incorrect_label["text"] = (
                f"Incorrect: {int(self._scoring.total_scores().incorrect)}"
            )
            self._total_questions_label["text"] = (
                f"Total questions: {int(self._scoring.total_scores().total_questions)}"
            )

            self.answered_times = 0
            self.started_recording = False
            self.rerolled += 1
            self._record_button["state"] = "normal"
            self._next_question_button["state"] = "disabled"

    def update_window_size(self):
        lines = np.ceil(len(self.current_sentence) / 80)
        if self._user_answer is not None:
            lines += np.ceil(len(self._user_answer.get("1.0", tk.END)) / 80)
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
        button_exit = tk.Button(
            popup, text="Ok", command=lambda: self.close_connection_error_popup(popup)
        )
        button_exit.configure(background="black", foreground="white")
        button_exit.grid(row=1, column=1)
        popup.lift()

    def close_connection_error_popup(self, popup):
        self.connection_error_popup = False
        if self.answered_times < 1:
            self._record_button["state"] = "normal"
        if self.rerolled < 1:
            self._next_question_button["state"] = "normal"
        popup.destroy()

    def run_locally(self, popup, process_last_recording):
        loading = self.loading_popup("Loading", "Loading... ")
        self._speech2text.__init__(run_locally=True)
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


def main():
    parser = argparse.ArgumentParser(description="Reading App")
    parser.add_argument(
        "--sentences",
        type=str,
        default="data/sentences.txt",
        help="Path to sentences.txt",
    )
    args = parser.parse_args()

    # Now you can access the sentences file path with args.sentences
    sentences_file_path = Path(args.sentences)
    if not sentences_file_path.exists():
        print(f"File {sentences_file_path} does not exist. ")

    # Continue with your application logic
    app = ReadingApp(sentences_file_path)
    app.window.mainloop()


if __name__ == "__main__":
    main()
