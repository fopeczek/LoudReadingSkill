import tkinter as tk
import time
from pydub import AudioSegment
from pydub.playback import play
from threading import Thread

from scoring import Scoring, score_sentence, calc_time_penalty
from recorder import Recorder
from speech2text import Speech2Text


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

    def __init__(self):
        self.started_recording = False
        self.answered_times = 0
        self.rerolled = 0

        self.current_sentence = None
        self._user_answer = None
        self.time_start = 0.
        self.time_taken = 0.

        self._scoring = Scoring()
        self._recorder = Recorder()

        self._speech2text = Speech2Text(run_locally=False)

        self._window = tk.Tk()
        self._window.title("Reading")
        self._window.configure(bg='black')

        self._question_text = tk.Text(self._window, height=1, background='black', foreground='white')
        self._question_text.pack()

        self._record_button = tk.Button(self._window, text="Record")
        self._record_button.configure(background='black', foreground='white')
        self._record_button.bind("<ButtonPress>", self.toggle_recording)
        self._window.bind("<KeyPress>", self.toggle_recording)
        self._record_button.pack()

        self._next_question_button = tk.Button(self._window, text="Next question")
        self._next_question_button.configure(background='black', foreground='white')
        self._next_question_button.bind("<ButtonPress>", self.next_question)
        self._next_question_button.pack()

        self._accuracy_score_label = tk.Label(self._window, text=f"Accuracy: {self._scoring.total_scores().accuracy}")
        self._accuracy_score_label.configure(background='black', foreground='white')
        self._accuracy_score_label.pack()

        self._time_score_label = tk.Label(self._window, text=f"Speed: {self._scoring.total_scores().speed}")
        self._time_score_label.configure(background='black', foreground='white')
        self._time_score_label.pack()

        self._correct_label = tk.Label(self._window, text=f"Correct: {self._scoring.total_scores().correct}")
        self._correct_label.configure(background='black', foreground='white')
        self._correct_label.pack()

        self._incorrect_label = tk.Label(self._window, text=f"Incorrect: {self._scoring.total_scores().incorrect}")
        self._incorrect_label.configure(background='black', foreground='white')
        self._incorrect_label.pack()

        self._total_questions_label = tk.Label(self._window,
                                               text=f"Total questions: {self._scoring.total_scores().total_questions}")
        self._total_questions_label.configure(background='black', foreground='white')
        self._total_questions_label.pack()

        self._user_answer = tk.Text(self._window, height=1, background='black', foreground='white')
        self._user_answer.pack()
        self._user_answer.destroy()

        self.next_question()

    def toggle_recording(self, event):
        if event.keysym == "space" or event.widget == self._record_button:
            if not self.started_recording:
                if self.answered_times < 1:
                    self.start_recording()
            else:
                self.stop_recording()

    def start_recording(self):
        self.time_taken = time.time() - self.time_start
        self._recorder.start_recording()
        self.started_recording = True
        self._record_button['state'] = 'active'

    def stop_recording(self):
        self._recorder.stop_recording()
        self.started_recording = False
        sound = self._recorder.get_last_recording()
        if sound.length() < 1.0:
            return
        transcript = self._speech2text.get_transcript(sound)
        if not transcript or len(transcript) < 1 or transcript == '""':
            return

        self.answered_times += 1
        self.rerolled = 0
        self._record_button['state'] = 'disabled'
        self._next_question_button['state'] = 'normal'

        self._user_answer = tk.Text(self._window, height=1, background='black', foreground='white')
        self._user_answer.delete('1.0', tk.END)
        self._user_answer.insert(tk.END, transcript)
        self._user_answer.pack()

        self.check_answer(transcript)

    def insert_colored_text(self, html_text):
        import re
        pattern = re.compile(r"<span style='background-color: #FF0000'>(.*?)</span>")
        last_end = 0
        self._question_text.config(state='normal')  # Enable the Text widget before inserting text
        self._question_text.delete('1.0', tk.END)
        for match in pattern.finditer(html_text):
            self._question_text.insert(tk.END, html_text[last_end:match.start()])
            self._question_text.insert(tk.END, match.group(1), 'highlight')
            last_end = match.end()
        self._question_text.insert(tk.END, html_text[last_end:])
        self._question_text.tag_config('highlight', foreground='red')
        self._question_text.config(state='disabled')  # Disable the Text widget after inserting text

    def check_answer(self, transcript):
        accuracy, redacted_answer_in_html = score_sentence(self.current_sentence, transcript)
        speed = calc_time_penalty(self.time_taken, self.current_sentence)
        self._accuracy_score_label['text'] += f" + {accuracy}"
        self._time_score_label['text'] += f" + {speed}"

        if self._scoring.update_total_scores(accuracy, speed):
            self._correct_label['text'] += " + 1"
            song = AudioSegment.from_mp3("correct.mp3")
            Thread(target=play, args=(song,)).start()
        else:
            self._incorrect_label['text'] += " + 1"
            song = AudioSegment.from_mp3("incorrect.mp3")
            Thread(target=play, args=(song,)).start()
        self._total_questions_label['text'] += " + 1"

        self._scoring.set_sentence_answer(self.current_sentence, transcript, accuracy, speed)
        self._question_text.delete('1.0', tk.END)
        self.insert_colored_text(redacted_answer_in_html)

    def next_question(self, event=None):
        if self.rerolled < 1:  # TODO replace 1 with max rerolls
            self.current_sentence = self._scoring.get_next_sentence()
            if self._user_answer is not None:
                self._user_answer.destroy()
            self.insert_colored_text(self.current_sentence)
            self.time_start = time.time()

            self._accuracy_score_label['text'] = f"Accuracy score: {self._scoring.total_scores().accuracy}"
            self._time_score_label['text'] = f"Time score: {self._scoring.total_scores().speed}"
            self._correct_label['text'] = f"Correct: {int(self._scoring.total_scores().correct)}"
            self._incorrect_label['text'] = f"Incorrect: {int(self._scoring.total_scores().incorrect)}"
            self._total_questions_label[
                'text'] = f"Total questions: {int(self._scoring.total_scores().total_questions)}"

            self.answered_times = 0
            self.started_recording = False
            self.rerolled += 1
            self._record_button['state'] = 'normal'
            self._next_question_button['state'] = 'disabled'

    @property
    def window(self):
        return self._window


def main():
    app = ReadingApp()
    app.window.mainloop()


if __name__ == "__main__":
    main()
