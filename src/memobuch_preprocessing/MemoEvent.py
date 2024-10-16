
class MemoEvent:
    """
    Represents an event for the memo project.
    """
    def __init__(self, id: str, title: str, person_ids: list[str], type: str, description: str, start_date: str, end_date: str, categories: list[str], location: str, latt: float, long: float):
        self.id = id
        self.title = title
        self.person_ids = person_ids
        self.type = type
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.categories = categories
        self.location = location
        self.latt = latt
        self.long = long


    def __repr__(self) -> str:
        return f"MemoEvent({self.id}, {self.title}, {self.person_ids}, {self.type}, {self.description}, {self.start_date}, {self.end_date}, {str(self.categories)}, {self.location}, {self.latt}, {self.long})"
