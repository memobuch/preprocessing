from typing import Literal
from memobuch_preprocessing.MemoEvent import MemoEvent


class MemoPerson:
    def __init__(self, id: str, last_name: str, first_name: str, maiden_name: str, alternative_spelling: str, gender: Literal["male", "female"], is_youth: bool, memorial_sign: str, biography_text: str, event: MemoEvent = None):
        self.id = id
        self.last_name = last_name
        self.first_name = first_name
        self.maiden_name = maiden_name
        self.alternative_spelling = alternative_spelling
        self.gender = gender
        self.is_youth = is_youth
        self.memorial_sign = memorial_sign
        self.biography_text = biography_text
        self.event = event

    def __repr__(self) -> str:
        return f"MemoPerson({self.id}, {self.last_name}, {self.first_name}, {self.maiden_name}, {self.alternative_spelling}, {self.gender}, {self.is_youth}, {self.memorial_sign}, {self.biography_text})"

