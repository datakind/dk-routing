from abc import ABC, abstractmethod

class OutputObjectBase(ABC):

    @abstractmethod
    def persist(self, file_manager):
        pass
