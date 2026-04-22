


class MemorPersonFile:
    """
    Data class representing files handled by the memo project.
    """

    def __init__(self, source_path: str, title: str, desc: str, source: str) -> None:
        self.source_path = source_path
        self.title = title
        self.desc = desc
        self.source = source

    def __repr__(self) -> str:
        """
        Returns a string representation of the MemoPersonFile object.
        :return: A string describing the image.
        """
        return f"MemoPersonFile(Path: {self.source_path}, Title: {self.title}, Description: {self.desc})"
        