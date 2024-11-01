from abc import ABC, abstractmethod
from core import VoiceSample


class ISpeech2Text(ABC):
    @abstractmethod
    def get_transcript(self, sound: VoiceSample) -> (bool, str):
        pass

    @abstractmethod
    def check(self) -> bool:
        pass


class IText2Speech(ABC):
    @abstractmethod
    def get_sound(self, text: str) -> VoiceSample:
        pass

    @abstractmethod
    def check(self) -> bool:
        pass
