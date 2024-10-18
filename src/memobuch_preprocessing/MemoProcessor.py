import csv
import os
import logging
import pandas as pd

from memobuch_preprocessing.GSheet import GSheet
from memobuch_preprocessing.MemoEvent import MemoEvent
from memobuch_preprocessing.MemoPerson import MemoPerson
from memobuch_preprocessing.MemoStatics import MemoStatics


class MemoProcessor:

    memo_persons: list[MemoPerson] = []
    memo_events: list[MemoEvent] = []

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
            # TODO entries in ghseets might be optional! - must introduce some kind of check
            birth_date = MemoProcessor._convert_date(person_entry['Geburtsdatum'])

            cur_memo_person = MemoPerson(
                id=MemoStatics.PROJECT_ABBR + ".person." +  str(person_entry['Identifikatornummer']), # required
                last_name=person_entry['Nachname'], # required
                first_name=person_entry['Vorname'], # optional
                maiden_name=person_entry['Mädchenname'], # optional
                alternative_spelling=person_entry['Alternative Schreibweise'], # optional
                is_youth=person_entry['Jugendlich'] == 'ja', # required
                gender=person_entry['Geschlecht'], # required
                memorial_sign=person_entry['Erinnerungszeichen (DERLA Nummer)'], # optional
                biography_text=person_entry['Freitext / Biografie'], # optional
                birth_place=person_entry['Geburtsort'], # optional
                birth_date=birth_date # optional
            )

            self.memo_persons.append(cur_memo_person)


        # Reading in Events from the gsheet
        for event_entry in self.memo_events_frame.to_dict(orient='records'):
            self.logger.info(f"Processing event entry from gsheet: {event_entry}")
            person_numbers = event_entry['Personennummer'].split(", ")
            person_ids = []
            for person_id in person_numbers:
                person_ids.append(MemoStatics.PROJECT_ABBR + ".person." + str(person_id))

            # split the categories by comma - BUT ignore commas within quotes (because of return from gsheets)
            person_categories = MemoProcessor.split_ignoring_quotes(event_entry['Kategorie'], ',')

            cur_memo_event = MemoEvent(
                id=event_entry['Id'],
                title=event_entry['Titel'],
                person_ids=person_ids,
                type=event_entry['Typ'],
                description=event_entry['Beschreibung'],
                start_date=MemoProcessor._convert_date(event_entry['Startdatum']),
                end_date=MemoProcessor._convert_date(event_entry['Enddatum']),
                categories=person_categories,
                location=event_entry['Ort'],
                latt=event_entry['Längengrad'],
                long=event_entry['Breitengrad'])

            self.logger.debug(f"Constructed memo event: {cur_memo_event}")
            self.memo_events.append(cur_memo_event)

        for person in self.memo_persons:
            for event in self.memo_events:
                if person.id in event.person_ids:
                    person.events.append(event)
                    self.logger.debug(f"Linking person {person.id} to event {event.id}. Constructed memo person: {person}")

            self.logger.info(f"Loaded memo person: {person}")


    def output_data(self):
        """
        Output the data to the output folder
        :return:
        """
        for person in self.memo_persons:
            folder_name = person.id
            folder_path = os.path.join(MemoStatics.OUTPUT_DIR, str(folder_name))
            os.makedirs(folder_path, exist_ok=True)

            person.write_as_dublin_core()
            person.write_as_object_csv()
            person.write_as_rdf_xml()
            person.write_as_search_json()
            person.write_as_datastreams_csv()
            self.logger.debug(f"Outputted digital object: {folder_path}")


    def clear_output_folder(self, output_root):
        """
        Clears the output folder. Skips folder with name containing 'material' and the README.md file
        :param output_root:
        :return:
        """
        self.logger.debug(f"Clearing output folder: {output_root}")
        for item in os.listdir(output_root):
            item_path = os.path.join(output_root, item)
            if os.path.isfile(item_path) and item != 'README.md':
                os.remove(item_path)
                self.logger.info(f"Deleted file: {item_path}")
            elif os.path.isdir(item_path):
                # skip folder if it contains 'material'
                if 'material' in item:
                    self.logger.debug(f"Skipping deletion of folder: {item_path}")
                    continue
                for root, dirs, files in os.walk(item_path, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                        self.logger.info(f"Deleted file: {os.path.join(root, name)}")
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                        self.logger.info(f"Deleted directory: {os.path.join(root, name)}")
                os.rmdir(item_path)
                self.logger.info(f"Deleted directory: {item_path}")


    @staticmethod
    def split_ignoring_quotes(text, delimiter):
        """
        Split a string by a delimiter, but ignore the delimiter if it is within quotes
        :param text: The text to split
        :param delimiter: The delimiter to split by
        :return: A list of the split text
        """
        result = []
        in_quotes = False
        current = ""
        for char in text:
            if char == '"':
                in_quotes = not in_quotes
            elif char == delimiter and not in_quotes:
                result.append(current)
                current = ""
            else:
                current += char

        result.append(current)

        # strip the results
        for i in range(len(result)):
            result[i] = result[i].strip()

        return result

    @staticmethod
    def _convert_date(date: str):
        """
        Converts a date from the format dd.mm.yyyy to the format yyyy-mm-dd
        :param date: The date to convert
        :return: The converted date
        """
        day, month, year = date.split('.')
        return f"{year}-{month}-{day}T00:00:00Z"