
# TODO finish impl
# to make it easier to create MemoPerson objects
class MemoPerson:
    def __init__(self, id: int, last_name: str, first_name: str, maiden_name: str, alternative_spelling: str, gender: str, is_youth: bool, memorial_sign: str, biography_text: str):
        self.id = id
        self.last_name = last_name
        self.first_name = first_name
        self.maiden_name = maiden_name
        self.alternative_spelling = alternative_spelling
        self.gender = gender
        self.is_youth = is_youth
        self.memorial_sign = memorial_sign
        self.biography_text = biography_text

    def __repr__(self) -> str:
        return f"MemoPerson({self.id}, {self.last_name}, {self.first_name}, {self.maiden_name}, {self.alternative_spelling}, {self.gender}, {self.is_youth}, {self.memorial_sign}, {self.biography_text})"

