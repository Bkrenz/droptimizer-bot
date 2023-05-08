from abc import ABC, abstractmethod


class AbstractApiDto(ABC):

    @abstractmethod
    def build_from_id(self):
        pass
