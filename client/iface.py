from abc import ABC, abstractmethod


class ISpeech2Text(ABC):
    @abstractmethod
    def get_transcript(self, sound) -> (bool, str):
        pass

    @abstractmethod
    def check(self) -> bool:
        pass
