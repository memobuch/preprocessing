from typing import Literal


class MemoEvent:
    """
    Represents an event for the memo project.
    (Needed for Haft- and Fluchtorte)
    """
    def __init__(self, id: str, title: str, event_type: Literal["haft", "flucht"], description: str, date: str, location: str, long: float, lat: float,):
        self.id = id
        self.title = title
        self.type = event_type # haftort or fluchtort
        self.description = description
        self.location = location
        self.long = long
        self.lat = lat
        self.date = date


    def __repr__(self) -> str:
        return f"MemoEvent({self.id}, {self.title}, {self.type}, {self.description}, {self.date}, {self.location}, {self.lat}, {self.long})"
