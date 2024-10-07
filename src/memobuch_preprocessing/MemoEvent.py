from memobuch_preprocessing.MemoPerson import MemoPerson


class MemoEvent:
    """
    Represents an event for the memo project.
    """
    def __init__(self, id: str, title: str, type: str, description: str, start_date: str, end_date: str, category: str, location: str, latt: float, long: float):
        self.id = id
        self.title = title
        self.type = type
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.category = category
        self.location = location
        self.latt = latt
        self.long = long
