from typing import Literal


class MemorEvent:
    """
    Represents an event for the memor project.
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
        return f"MemorEvent({self.id}, {self.title}, {self.type}, {self.description}, {self.date}, {self.location}, {self.lat}, {self.long})"
