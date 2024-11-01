from __future__ import annotations

import base64
import wave
from pathlib import Path

import numpy as np
from pydantic import BaseModel, field_serializer, field_validator
from pydub import AudioSegment
from pydub.playback import play


class VoiceSample(BaseModel):
    data: bytes
    frame_rate: int
    sample_width: int = 2
    channels: int = 1

    @field_validator("data", mode="before")
    @classmethod
    def validate_data(cls, data: bytes) -> bytes:
        if isinstance(data, str):
            return base64.b85decode(data)
        else:
            assert isinstance(data, bytes)
            return data

    @field_serializer("data")
    def serialize_data(self, data: bytes, _info):
        return base64.b85encode(data)

    def get_sample_as_np_array(self) -> np.ndarray:
        audio_segment = AudioSegment(
            self.data,
            frame_rate=self.frame_rate,
            sample_width=self.sample_width,
            channels=self.channels,
        )

        if self.frame_rate != 16000:  # 16 kHz
            audio_segment = audio_segment.set_frame_rate(16000)
        arr = np.array(audio_segment.get_array_of_samples())
        arr = arr.astype(np.float32) / 32768.0
        return arr / np.max(np.abs(arr))

    def ResampledClone(self, frame_rate: int = 16000) -> VoiceSample:
        audio_segment = AudioSegment(
            self.data,
            frame_rate=self.frame_rate,
            sample_width=self.sample_width,
            channels=self.channels,
        )

        audio_segment = audio_segment.set_frame_rate(frame_rate)
        return VoiceSample(
            data=audio_segment.raw_data,
            frame_rate=frame_rate,
            sample_width=self.sample_width,
        )

    def save(self, filename: Path):
        # create a new wave file
        open(str(filename), "a").close()
        with wave.open(str(filename), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.sample_width)
            wf.setframerate(self.frame_rate)
            wf.writeframes(self.data)

    def __len__(self):
        return len(self.data)

    @property
    def data(self):
        return self.data

    def play(self):
        audio = AudioSegment(
            self.data,
            frame_rate=self.frame_rate,
            sample_width=self.sample_width,
            channels=self.channels,
        )
        play(audio)

    def length(self):
        return len(self.data) / self.frame_rate / self.sample_width


def test_voice_sample() -> VoiceSample:
    data = "ala ma kota".encode()
    print(data)
    frame_rate = 44100
    print(base64.b85encode(data))
    sample_width = 2
    voice_sample = VoiceSample(
        data=data, frame_rate=frame_rate, sample_width=sample_width
    )
    print(str(voice_sample))
    print(voice_sample.model_dump_json())
    return voice_sample


def voice_sample_from_wav(wav_file: Path) -> VoiceSample:
    with wave.open(str(wav_file), "rb") as wf:
        data = wf.readframes(wf.getnframes())
        frame_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        return VoiceSample(data=data, frame_rate=frame_rate, sample_width=sample_width)


if __name__ == "__main__":
    json_txt = test_voice_sample().json()
    with open("test.json", "w") as f:
        f.write(json_txt)

    voice_sample = VoiceSample.parse_raw(json_txt)
    print(f"voice_sample: {voice_sample}")
