import numpy as np
import pyaudio
from pathlib import Path

from core import VoiceSample


class Recorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []

    def start_recording(self):
        self.frames = []
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            input=True,
            frames_per_buffer=1024,
            stream_callback=self.callback,
        )
        self.stream.start_stream()

    def stop_recording(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.stream = None

    def get_last_recording(self) -> VoiceSample:
        return VoiceSample(data=b"".join(self.frames), frame_rate=44100, sample_width=2)

    def get_last_recording_as_whisper_sound(self) -> np.ndarray:
        sound = self.get_last_recording()
        return sound.get_sample_as_np_array()

    def save_last_recording(self, filename: str):
        return self.get_last_recording().save(Path(filename))

    def play_last_recording(self):
        stream = self.p.open(
            format=pyaudio.paInt16, channels=2, rate=44100, output=True
        )
        stream.write(b"".join(self.frames))
        stream.stop_stream()

    def callback(self, in_data, frame_count, time_info, status):
        self.frames.append(in_data)
        return (in_data, pyaudio.paContinue)
