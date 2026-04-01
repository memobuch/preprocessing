import csv
import json
import os
import shutil
import logging
from datetime import datetime
from typing import Literal

import pandas as pd

from memobuch_preprocessing.GSheet import GSheet
from memobuch_preprocessing.MemoEvent import MemoEvent
from memobuch_preprocessing.MemoVocab import MemoVocab
from memobuch_preprocessing.Person.MemoPerson import MemoPerson
from memobuch_preprocessing.MemoStatics import MemoStatics
from memobuch_preprocessing.Person.MemoPersonFile import MemoPersonFile
from memobuch_preprocessing.geo.FeatureAggregator import FeatureAggregator


class MemoProcessor:

    memo_persons: list[MemoPerson] = []
    memo_events: list[MemoEvent] = []

    memo_persons_frame: pd.DataFrame
    memo_events_frame: pd.DataFrame
    logger: logging.Logger

    MATERIAL_ROOT_PATH = MemoStatics.MATERIAL_ROOT_PATH

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
        # self.memo_events_frame = GSheet.request_public_sheet("1O0WHyEKA-IZc7L6iXVEbArsuuhK9PMStXhy3kZDUpi0", "Ereignisse")

        # self.logger.info(f"Memo Persons: {self.memo_persons_frame}")
        # self.logger.info(f"Memo Events: {self.memo_events_frame}")

        self.logger.info("Processing memo persons")
        persons_dict = self.memo_persons_frame.to_dict(orient='records')

        # Reading in the persons from the gsheet
        for person_entry in persons_dict:
            # first handle building memo person id (somewhat only required field)
            memo_person_col_id = str(person_entry['Identifikatornummer'])
            self.logger.info(f"Processing person entry from gsheet: {memo_person_col_id}")
            # if no identifier number is given, skip the entry
            if memo_person_col_id.isspace() or len(memo_person_col_id) == 0:
                self.logger.error(f"Missing identifier number for person entry: {person_entry}. Skipping entry.")
                continue
            memo_person_id = f"{MemoStatics.PROJECT_ABBR}.person.{memo_person_col_id}"

            try:
                cur_memo_person = MemoPerson(
                    id=memo_person_id, # required
                    last_name= MemoProcessor.map_nullable_col(person_entry['Nachname']), # optional
                    first_name=MemoProcessor.map_nullable_col(person_entry['Vorname']), # optional
                    maiden_name=MemoProcessor.map_nullable_col(person_entry['Mädchenname']), # optional
                    alternative_spelling=MemoProcessor.map_nullable_col(person_entry['Alternative Schreibweise']), # optional
                    is_youth=MemoProcessor.map_is_youth_col(person_entry['Jugendlich']), # required
                    gender=MemoProcessor.map_gender_col(person_entry['Geschlecht']), # required
                    memorial_signs=MemoProcessor.map_memorial_signs(person_entry['Erinnerungszeichen (DERLA Nummer)']), # optional
                    biography_text=MemoProcessor.map_nullable_col(person_entry['Biografie']), # optional
                    birth_place=MemoProcessor.map_nullable_col(person_entry['Geburtsort']), # optional
                    birth_date=MemoProcessor.map_nullable_col(person_entry['Geburtsdatum']), # optional
                    death_date=MemoProcessor.map_nullable_col(person_entry['Todesdatum']), # optional
                    death_place=MemoProcessor.map_nullable_col(person_entry['Sterbeort (Bezeichnung)']),
                    death_longitude=MemoProcessor.map_nullable_col(person_entry['Längengrad (Sterbeort)']),
                    death_lattitude=MemoProcessor.map_nullable_col(person_entry['Breitengrad (Sterbeort)']),
                    voluntary_address=MemoProcessor.map_nullable_col(person_entry["Letzte freiwillige Wohnadresse"]),
                    voluntary_longitude=MemoProcessor.map_nullable_col(person_entry["Längengrad (freiwillige Wohnadresse)"]),
                    voluntary_latitude=MemoProcessor.map_nullable_col(person_entry["Breitengrad (freiwillige Wohnadresse)"]),
                    forced_address=MemoProcessor.map_nullable_col(person_entry["Letzte erzwungene Wohnadresse"]),
                    forced_longitude=MemoProcessor.map_nullable_col(person_entry["Längengrad (erzwungene Wohnadresse)"]),
                    forced_latitude=MemoProcessor.map_nullable_col(person_entry["Breitengrad (erzwungene Wohnadresse)"]),
                    victim_category=MemoProcessor.map_victim_categories(person_entry['Opferkategorie']),
                    literature=MemoProcessor.map_nullable_col(person_entry["Literatur"]),
                )
            except Exception as e:
                self.logger.error(f"Error creating MemoPerson for entry - Skipping person: {person_entry}: {e}")
                continue

            # image logic must be here now
            person_folder_path = f"{self.MATERIAL_ROOT_PATH}{str(person_entry['Identifikatornummer'])}"

            try:
                if not os.path.exists(person_folder_path):
                    msg = f"No gdrive folder found for person (from table): {cur_memo_person.id} at expected path: {person_folder_path}. Every should have a folder defined!"
                    self.memo_persons.append(cur_memo_person)
                    raise FileNotFoundError(msg)

                # image loading per person
                person_img_metadata_path = f"{person_folder_path}{os.sep}img.txt"
                person_img_files_path = f"{person_folder_path}{os.sep}img"

                entries = self._load_metadata_csv(person_img_metadata_path)
                for entry in entries:
                    cur_image_path = f"{person_img_files_path}{os.path.sep}{entry['Dateiname']}"
                    memo_image = MemoPersonFile(
                        source_path=cur_image_path,
                        title=entry["Titel"],
                        desc=entry["Beschreibung"]
                    )
                    cur_memo_person.add_image(memo_image)

                ### Transforming Haftorte to memo events
                person_haftorte_metadata_path = f"{person_folder_path}{os.sep}haftorte.txt"
                haftorte_entries = self._load_metadata_csv(person_haftorte_metadata_path)
                for i, haftort in enumerate(haftorte_entries):
                    event = MemoEvent(
                        id=f"{cur_memo_person.id}_event_haft_{i}",
                        event_type="haft",
                        title=haftort["Titel"],
                        description=haftort["Beschreibung"],
                        location=haftort["Ort"],
                        long=haftort["Längengrad"],
                        lat=haftort["Breitengrad"],
                        date=haftort["Datum"]
                    )
                    cur_memo_person.add_event(event)

                # handling of fluchtorte (to MemoEvents)
                person_fluchtorte_metadata_path = f"{person_folder_path}{os.sep}fluchtorte.txt"
                fluchtorte_entries = self._load_metadata_csv(person_fluchtorte_metadata_path)
                for i, fluchtort in enumerate(fluchtorte_entries):
                    event = MemoEvent(
                        id=f"{cur_memo_person.id}_event_flucht_{i}",
                        event_type="flucht",
                        title=fluchtort["Titel"],
                        description=fluchtort["Beschreibung"],
                        location=fluchtort["Ort"],
                        long=fluchtort["Längengrad"],
                        lat=fluchtort["Breitengrad"],
                        date=fluchtort["Datum"]
                    )
                    cur_memo_person.add_event(event)

                # Adding arbitrary documents to a memo person
                person_documents_metadata_path = f"{person_folder_path}{os.sep}files.txt"
                documents_entries = self._load_metadata_csv(person_documents_metadata_path)
                for i, person_document in enumerate(documents_entries):
                    document = MemoPersonFile(
                        title=person_document["Titel"],
                        desc=person_document["Beschreibung"],
                        source_path=f"{person_folder_path}{os.path.sep}files{os.path.sep}{person_document['Dateiname']}",
                    )
                    cur_memo_person.add_document(document)

            except Exception as e:
                self.logger.warning(f"Error loading material files for person {cur_memo_person.id} at path {person_folder_path}: {e}")
            finally:
                # as final step add the person
                self.memo_persons.append(cur_memo_person)
                self.logger.info(f"Loaded memo person: {cur_memo_person}")

        # Reading in Events from the gsheet
        # for event_entry in self.memo_events_frame.to_dict(orient='records'):
        #     self.logger.info(f"Processing event entry from gsheet: {event_entry}")
        #     person_numbers = event_entry['Personennummer'].split(", ")
        #     person_ids = []
        #     for person_id in person_numbers:
        #         person_ids.append(MemoStatics.PROJECT_ABBR + ".person." + str(person_id))
        #
        #     # split the categories by comma - BUT ignore commas within quotes (because of return from gsheets)
        #     person_categories = MemoProcessor.split_ignoring_quotes(event_entry['Kategorie'], ',')
        #
        #     cur_memo_event = MemoEvent(
        #         id=event_entry['Id'],
        #         title=event_entry['Titel'],
        #         person_ids=person_ids,
        #         type=event_entry['Typ'],
        #         description=event_entry['Beschreibung'],
        #         start_date=MemoProcessor._convert_date(event_entry['Startdatum']),
        #         end_date=MemoProcessor._convert_date(event_entry['Enddatum']),
        #         categories=person_categories,
        #         location=event_entry['Ort'],
        #         latt=event_entry['Längengrad'],
        #         long=event_entry['Breitengrad'])
        #
        #     self.logger.debug(f"Constructed memo event: {cur_memo_event}")
        #     self.memo_events.append(cur_memo_event)

        # for person in self.memo_persons:
        #     for event in self.memo_events:
        #         if person.id in event.person_ids:
        #             person.events.append(event)
        #             self.logger.debug(f"Linking person {person.id} to event {event.id}. Constructed memo person: {person}")
        #
        #     self.logger.info(f"Loaded memo person: {person}")

    def _load_metadata_csv(self, path: str):
        """
        Reads given file path as csv and returns a list of dictionary representing each row.
        Handles BOM, whitespace, and provides diagnostic logging.

        :param path: Path to the file that should be read
        :return: list of dictionaries representing each row. Key value is of head row.
        """
        rows = []
        if not os.path.exists(path):
            self.logger.error(f"No metadata file at {path} found!")
            return rows

        with open(path, "r", encoding="utf-8-sig") as txt_file:  # Handle BOM
            csv_reader = csv.DictReader(
                txt_file,
                delimiter=',',
                quotechar="'",
                skipinitialspace=True  # Ignore spaces after delimiter
            )

            # Log headers for debugging
            if csv_reader.fieldnames:
                self.logger.debug(f"CSV columns in {path}: {csv_reader.fieldnames}")

            for row in csv_reader:
                rows.append(row)

        return rows


    def output_data(self):
        """
        Output the data to the output folder
        :return:
        """
        for person in self.memo_persons:
            folder_name = person.id
            folder_path = os.path.join(MemoStatics.OUTPUT_DIR, str(folder_name))
            os.makedirs(folder_path, exist_ok=True)

            try:
                person.write_as_dublin_core()
                person.write_as_object_csv()
                person.write_as_rdf_xml()
                person.write_as_turtle()
                person.write_as_search_json()
                person.write_as_image_files()
                person.write_as_document_files()
                person.write_as_geojson()
                person.write_as_datastreams_csv()
                self.logger.info(f"Outputted digital object: {folder_path}")
            except Exception as e:
                logging.error(f"SKIPPING writing output files for memo person: {person.id} - Error writing digital object at path: {folder_path}: {e}")
                try:
                    shutil.rmtree(folder_path)
                except Exception as cleanup_error:
                    logging.error(f"Failed to remove folder {folder_path}: {cleanup_error}")


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
    def map_nullable_col(col_value) -> str | None:
        """
        Maps a column value to None if it is a placeholder for null values.
        :param col_value: The column value to map
        :return: The mapped column value or None
        """
        col_value = str(col_value)
        col_value = col_value.strip()
        if col_value == "-":
            return None

        if col_value.isspace():
            return None

        if len(col_value) == 1:
            return None

        if len(col_value) == 0:
            return None

        if pd.isna(col_value):
            return None

        # if the column is parseable as float then it should not be Nan!
        try:
            parseable_as_float = float(col_value)
            if pd.isna(parseable_as_float):
                return None
        except:
            pass

        return col_value

    @staticmethod
    def map_is_youth_col(col_value) -> bool:
        """
        Maps a column value to a boolean indicating youth status.
        :param col_value: The column value to map
        :return: True if the value indicates youth, False otherwise
        """

        col_value = str(col_value)
        col_value = col_value.strip().lower()
        if col_value == "ja":
            return True
        elif col_value == "nein":
            return False
        else:
            raise ValueError(f"Invalid column value 'jugendlich': {col_value}")


    @staticmethod
    def map_gender_col(col_value) -> Literal["male", "female"]:
        """
        Maps a column value to a standardized gender
        """
        col_value = str(col_value)
        col_value = col_value.strip().lower()
        if col_value == "männlich":
            return "male"
        elif col_value == "weiblich":
            return "female"
        else:
            msg = f"Invalid gender column: {col_value}"
            logging.error(msg)
            raise ValueError(msg)

    @staticmethod
    def map_victim_categories(col) -> list[str]:
        """
        Extracts all unique victim categories from the memo persons
        :return: A set of unique victim categories
        """

        try:
            col = MemoProcessor.map_nullable_col(col)
            victim_categories = col.split(",")
            victim_categories = [cat.strip() for cat in victim_categories]
            return victim_categories
        except Exception as e:
            msg = f"Error analysing victim categories. There might be no victim categories assigned - assigning default empty list {e}"
            logging.warning(msg)
            return []

    @staticmethod
    def map_memorial_signs(col):
        """
        Maps memorial signs from the column value
        """
        try:
            col = MemoProcessor.map_nullable_col(col)
            memorial_signs = col.split(";")
            memorial_signs = [sign.strip() for sign in memorial_signs]
            return memorial_signs
        except Exception as e:
            msg = f"Error analysing memorial signs. There might be no memorial signs assigned - assigning default empty list {e}"
            logging.warning(msg)
            return []


    def output_person_list_object(self):
        """
        Creates a object folder (with datastreams.csv / object.csv) containing all persons data as GEOJSON
        :return:
        """

        # first create folder
        object_id = "memo.person-register"
        folder_path = os.path.join(MemoStatics.OUTPUT_DIR, str(object_id))
        os.makedirs(folder_path, exist_ok=True)

        # create aggregated geojson file
        all_features = []
        for person in self.memo_persons:
            person_features = person.to_geojson_features()
            all_features.extend(person_features)

        # aggregate features with same coordinates
        # **NEW: Deduplicate features with identical coordinates**
        self.logger.info(f"Original feature count: {len(all_features)}")
        deduplicated_features = FeatureAggregator().deduplicate_geojson_features(all_features)
        self.logger.info(f"Deduplicated feature count: {len(deduplicated_features)}")

        # Statistics
        # TODO update tag count?
        # event_type_counts = {}
        # for feature in deduplicated_features:
        #     event_type = feature['properties']['event_type']
        #     event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        geojson = {
            "type": "FeatureCollection",
            "vocab": MemoVocab.VOCAB_CONTAINER,
            "metadata": {
                "project": "MEMO - Digitales Memobuch",
                "total_persons": len(self.memo_persons),
                "total_location_events": len(deduplicated_features),
                # "event_type_counts": event_type_counts,
                "generated": datetime.now().isoformat()
            },
            "features": deduplicated_features
        }

        json_path = os.path.join(folder_path, 'EVENTS.json')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)


        self.logger.info(f"Outputted all persons GEOJSON object: {json_path}")

        # Create dublin core xml
        dc_xml_string = f"""
            <oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                   xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">
                <dc:identifier>{object_id}</dc:identifier>
                <dc:creator>Born digital - memo project GAMS</dc:creator>
                <dc:title xml:lang="en">Ernst Altmann</dc:title>
                <dc:subject>Register</dc:subject>
                <dc:rights>Creative Commons BY-NC 4.0</dc:rights>
                <dc:description xml:lang="de">Personenregister des Memo Projekts</dc:description>
                <dc:date>2025/26</dc:date>
                <dc:language>de</dc:language>
                <dc:publisher>Heimo Halbrainer</dc:publisher>
                <dc:rights>Creative Commons BY-NC 4.0</dc:rights>
                <dc:rights>https://creativecommons.org/licenses/by-nc/4.0</dc:rights>
                <dc:type>Dataset</dc:type>
                <dc:format>Born digital: Eintrag in google Tabelle</dc:format>
            </oai_dc:dc>
        """
        dc_xml_path = os.path.join(folder_path, "DC.xml")
        with open(dc_xml_path, "w", encoding="utf-8") as dc_file:
            dc_file.write(dc_xml_string.strip())
        self.logger.info(f"Outputted all persons DC.xml: {dc_xml_path}")

        # Creation of object.csv
        object_csv_path = os.path.join(folder_path, "object.csv")
        with open(object_csv_path, "w", encoding="utf-8", newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["recid", "title", "project", "description", "creator", "rights", "publisher", "source", "objectType", "mainResource", "tags"])
            csv_writer.writerow([object_id, "Personenregister", "memo", "Person registers and related indices for the MEMO project", "Born digital - memo project GAMS", "Creative Commons BY-NC 4.0", "memo project GAMS5", "Memo datasheet transformed by Memo preprocessing tool", "Dataset", "EVENTS.json", "register"])
        self.logger.info(f"Outputted all persons object.csv: {object_csv_path}")

        # Datastreams csv
        datastreams_csv_path = os.path.join(folder_path, "datastreams.csv")
        with open(datastreams_csv_path, "w", encoding="utf-8", newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["dsid","dspath", "title","mimetype", "description","creator","rights"])
            csv_writer.writerow(["EVENTS.json","EVENTS.json","All Persons as GEOJSON", "application/json", "GEOJSON file containing all persons","Born digital - memo project GAMS","Creative Commons BY-NC 4.0"])
            csv_writer.writerow(["DC.xml","DC.xml", "Dublin Core Metadata","application/xml", "Dublin Core metadata for the persons register","Born digital - memo project GAMS","Creative Commons BY-NC 4.0"])
        self.logger.info(f"Outputted all persons datastreams.csv: {datastreams_csv_path}")
