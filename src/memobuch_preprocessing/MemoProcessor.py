import os
import logging
import pandas as pd

from memobuch_preprocessing.GSheet import GSheet
from memobuch_preprocessing.MemoEvent import MemoEvent
from memobuch_preprocessing.MemoPerson import MemoPerson


class MemoProcessor:

    memo_persons: list = []
    memo_events: list = []

    memo_persons_frame: pd.DataFrame
    memo_events_frame: pd.DataFrame
    logger: logging.Logger


    def __init__(self):
        #
        # Configure logging
        log_file_path = 'log/application.log'
        if os.path.exists(log_file_path):
            os.remove(log_file_path)

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler()
        ])
        self.logger = logging.getLogger(__name__)

        #
        output_root = 'output'
        os.makedirs(output_root, exist_ok=True)
        self.clear_output_folder(output_root)


    def load_data(self):

        self.memo_persons_frame = GSheet.request_public_sheet("1O0WHyEKA-IZc7L6iXVEbArsuuhK9PMStXhy3kZDUpi0", "Personen")
        self.memo_events_frame = GSheet.request_public_sheet("1O0WHyEKA-IZc7L6iXVEbArsuuhK9PMStXhy3kZDUpi0", "Ereignisse")

        self.logger.info(f"Memo Persons: {self.memo_persons_frame}")
        self.logger.info(f"Memo Events: {self.memo_events_frame}")

        self.logger.info("Processing memo persons")
        persons_dict = self.memo_persons_frame.to_dict(orient='records')


        # Reading in the persons from the gsheet
        for person_entry in persons_dict:
            # TODO entries in ghseets might be optional!
            self.logger.info(f"Processing person entry from gsheet: {person_entry}")
            cur_memo_person = MemoPerson(
                id=person_entry['Identifikatornummer'], # required
                last_name=person_entry['Nachname'], # required
                first_name=person_entry['Vorname'], # optional
                maiden_name=person_entry['Mädchenname'], # optional
                alternative_spelling=person_entry['Alternative Schreibweise'], # optional
                is_youth=person_entry['Jugendlich'] == 'ja', # required
                gender=person_entry['Geschlecht'], # required
                memorial_sign=person_entry['Erinnerungszeichen (DERLA Nummer)'], # optional
                biography_text=person_entry['Freitext / Biografie'] # optional

            )

            self.memo_persons.append(cur_memo_person)


        # Reading in Events from the gsheet
        for event_entry in self.memo_events_frame.to_dict(orient='records'):
            self.logger.info(f"Processing event entry from gsheet: {event_entry}")
            cur_memo_event = MemoEvent(
                id=event_entry['Id'],
                title=event_entry['Titel'],
                person_number=event_entry['Personennummer'],
                type=event_entry['Typ'],
                description=event_entry['Beschreibung'],
                start_date=event_entry['Startdatum'],
                end_date=event_entry['Enddatum'],
                category=event_entry['Kategorie'],
                location=event_entry['Ort'],
                latt=event_entry['Längengrad'],
                long=event_entry['Breitengrad'])

            self.memo_events.append(cur_memo_event)


        # Linking persons to events last
        for person in self.memo_persons:
            for event in self.memo_events:
                if event.person_number == person.id:
                    person.event = event


    def output_data(self):
        """
        Output the data to the output folder
        :return:
        """
        for person in self.memo_persons:
            self.logger.info(f"Memo Person: {person}")

        for event in self.memo_events:
            self.logger.info(f"Memo Event: {event}")





    def clear_output_folder(self, output_root):
        self.logger.debug(f"Clearing output folder: {output_root}")
        for item in os.listdir(output_root):
            item_path = os.path.join(output_root, item)
            if os.path.isfile(item_path) and item != 'README.md':
                os.remove(item_path)
                self.logger.info(f"Deleted file: {item_path}")
            elif os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                        self.logger.info(f"Deleted file: {os.path.join(root, name)}")
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                        self.logger.info(f"Deleted directory: {os.path.join(root, name)}")
                os.rmdir(item_path)
                self.logger.info(f"Deleted directory: {item_path}")
