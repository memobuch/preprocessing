import pandas as pd

class GSheet:
    """
    Class to handle Google Sheets
    """

    @staticmethod
    def request_public_sheet(sheet_id: str, sheet_name: str) -> pd.DataFrame:
        """
        Get a public Google Sheet
        """
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
        return pd.read_csv(url, encoding='utf-8', lineterminator='\n')