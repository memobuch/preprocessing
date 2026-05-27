import csv
import json
import os
import shutil
import logging
from datetime import datetime
from typing import Literal

import pandas as pd

from memorbuch_preprocessing.GSheet import GSheet
from memorbuch_preprocessing.MemorEvent import MemorEvent
from memorbuch_preprocessing.MemorVocab import MemorVocab
from memorbuch_preprocessing.Person.MemorPerson import MemorPerson
from memorbuch_preprocessing.MemorStatics import MemorStatics
from memorbuch_preprocessing.Person.MemorPersonFile import MemorPersonFile
from memorbuch_preprocessing.geo.FeatureAggregator import FeatureAggregator


class MemorProcessor:

    memor_persons: list[MemorPerson] = []
    memor_events: list[MemorEvent] = []

    memor_persons_frame: pd.DataFrame
    memor_events_frame: pd.DataFrame
    logger: logging.Logger

    MATERIAL_ROOT_PATH = MemorStatics.MATERIAL_ROOT_PATH

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

        self.memor_persons_frame = GSheet.request_public_sheet("1O0WHyEKA-IZc7L6iXVEbArsuuhK9PMStXhy3kZDUpi0", "Personen")
        # self.memor_events_frame = GSheet.request_public_sheet("1O0WHyEKA-IZc7L6iXVEbArsuuhK9PMStXhy3kZDUpi0", "Ereignisse")

        # self.logger.info(f"Memor Persons: {self.memor_persons_frame}")
        # self.logger.info(f"Memor Events: {self.memor_events_frame}")

        self.logger.info("Processing memor persons")
        persons_dict = self.memor_persons_frame.to_dict(orient='records')

        # Reading in the persons from the gsheet
        for person_entry in persons_dict:
            # first handle building memor person id (somewhat only required field)
            memor_person_col_id = str(person_entry['Identifikatornummer'])

            # fix if identifikatornummer ends with .0 against expectations
            if memor_person_col_id.endswith(".0"):
                memor_person_col_id = memor_person_col_id.replace(".0", "")

            self.logger.info(f"Processing person entry from gsheet: {memor_person_col_id}")
            # if no identifier number is given, skip the entry
            if memor_person_col_id.isspace() or len(memor_person_col_id) == 0:
                self.logger.error(f"Missing identifier number for person entry: {person_entry}. Skipping entry.")
                continue
            # gsheet might return the numbers as float with e.g. a "1" as "1.0" -> remove if needed
            if memor_person_col_id.endswith(".0"):
                memor_person_col_id = memor_person_col_id.replace(".0", "")

            memor_person_id = f"{MemorStatics.PROJECT_ABBR}.person.{memor_person_col_id}"

            try:
                cur_memor_person = MemorPerson(
                    id=memor_person_id, # required
                    last_name= MemorProcessor.map_nullable_col(person_entry['Nachname']), # optional
                    first_name=MemorProcessor.map_nullable_col(person_entry['Vorname']), # optional
                    maiden_name=MemorProcessor.map_nullable_col(person_entry['Mädchenname']), # optional
                    alternative_spelling=MemorProcessor.map_nullable_col(person_entry['Alternative Schreibweise']), # optional
                    is_youth=MemorProcessor.map_is_youth_col(person_entry['Jugendlich']), # required
                    gender=MemorProcessor.map_gender_col(person_entry['Geschlecht']), # required
                    memorial_signs=MemorProcessor.map_memorial_signs(person_entry['Erinnerungszeichen (DERLA Nummer)']), # optional
                    biography_text=MemorProcessor.map_nullable_col(person_entry['Biografie']), # optional
                    birth_place=MemorProcessor.map_nullable_col(person_entry['Geburtsort']), # optional
                    birth_date=MemorProcessor.map_nullable_col(person_entry['Geburtsdatum']), # optional
                    death_date=MemorProcessor.map_nullable_col(person_entry['Todesdatum']), # optional
                    death_place=MemorProcessor.map_nullable_col(person_entry['Sterbeort (Bezeichnung)']),
                    death_longitude=MemorProcessor.map_nullable_col(person_entry['Längengrad (Sterbeort)']),
                    death_lattitude=MemorProcessor.map_nullable_col(person_entry['Breitengrad (Sterbeort)']),
                    voluntary_address=MemorProcessor.map_nullable_col(person_entry["Letzte freiwillige Wohnadresse"]),
                    voluntary_longitude=MemorProcessor.map_nullable_col(person_entry["Längengrad (freiwillige Wohnadresse)"]),
                    voluntary_latitude=MemorProcessor.map_nullable_col(person_entry["Breitengrad (freiwillige Wohnadresse)"]),
                    forced_address=MemorProcessor.map_nullable_col(person_entry["Letzte erzwungene Wohnadresse"]),
                    forced_longitude=MemorProcessor.map_nullable_col(person_entry["Längengrad (erzwungene Wohnadresse)"]),
                    forced_latitude=MemorProcessor.map_nullable_col(person_entry["Breitengrad (erzwungene Wohnadresse)"]),
                    victim_category=MemorProcessor.map_victim_categories(person_entry['Opferkategorie']),
                    literature=MemorProcessor.map_nullable_col(person_entry["Literatur"]),
                )
            except Exception as e:
                self.logger.error(f"Error creating MemorPerson for entry - Skipping person: {person_entry}: {e}")
                continue

            # image logic must be here now
            person_folder_path = f"{self.MATERIAL_ROOT_PATH}{memor_person_col_id}"

            try:
                if not os.path.exists(person_folder_path):
                    msg = f"No gdrive folder found for person (from table): {cur_memor_person.id} at expected path: {person_folder_path}. Every should have a folder defined!"
                    raise FileNotFoundError(msg)

                # image loading per person
                person_img_metadata_path = f"{person_folder_path}{os.sep}img.txt"
                person_img_files_path = f"{person_folder_path}{os.sep}img"

                entries = self._load_metadata_csv(person_img_metadata_path)
                for entry in entries:
                    cur_image_path = f"{person_img_files_path}{os.path.sep}{entry['Dateiname']}"

                    # small fail safe if the column is not defined
                    source = ""
                    try:
                        source = entry["Quelle"]
                    except:
                        pass

                    memor_image = MemorPersonFile(
                        source_path=cur_image_path,
                        title=entry["Titel"],
                        desc=entry["Beschreibung"],
                        source=source
                    )
                    cur_memor_person.add_image(memor_image)

                ### Transforming Haftorte to memor events
                person_haftorte_metadata_path = f"{person_folder_path}{os.sep}haftorte.txt"
                haftorte_entries = self._load_metadata_csv(person_haftorte_metadata_path)
                for i, haftort in enumerate(haftorte_entries):
                    event = MemorEvent(
                        id=f"{cur_memor_person.id}_event_haft_{i}",
                        event_type="haft",
                        title=haftort["Titel"],
                        description=haftort["Beschreibung"],
                        location=haftort["Ort"],
                        long=haftort["Längengrad"],
                        lat=haftort["Breitengrad"],
                        date=haftort["Datum"]
                    )
                    cur_memor_person.add_event(event)

                # handling of fluchtorte (to MemorEvents)
                person_fluchtorte_metadata_path = f"{person_folder_path}{os.sep}fluchtorte.txt"
                fluchtorte_entries = self._load_metadata_csv(person_fluchtorte_metadata_path)
                for i, fluchtort in enumerate(fluchtorte_entries):
                    event = MemorEvent(
                        id=f"{cur_memor_person.id}_event_flucht_{i}",
                        event_type="flucht",
                        title=fluchtort["Titel"],
                        description=fluchtort["Beschreibung"],
                        location=fluchtort["Ort"],
                        long=fluchtort["Längengrad"],
                        lat=fluchtort["Breitengrad"],
                        date=fluchtort["Datum"]
                    )
                    cur_memor_person.add_event(event)

                # Adding arbitrary documents to a memor person
                person_documents_metadata_path = f"{person_folder_path}{os.sep}files.txt"
                documents_entries = self._load_metadata_csv(person_documents_metadata_path)
                for i, person_document in enumerate(documents_entries):

                    # small fail safe if the column is not defined
                    source = ""
                    try:
                        source = entry["Quelle"]
                    except:
                        pass

                    document = MemorPersonFile(
                        title=person_document["Titel"],
                        desc=person_document["Beschreibung"],
                        source_path=f"{person_folder_path}{os.path.sep}files{os.path.sep}{person_document['Dateiname']}",
                        source=source
                    )
                    cur_memor_person.add_document(document)
            except Exception as e:
                self.logger.debug(f"Error loading material files for person {cur_memor_person.id} at path {person_folder_path}: {e}")
            finally:
                # as final step add the person
                self.memor_persons.append(cur_memor_person)
                self.logger.debug(f"Loaded memor person: {cur_memor_person}")

        # display statistics
        logging.info(f"*** Successfully read in {len(self.memor_persons)} memor persons from gsheets")

        # Reading in Events from the gsheet
        # for event_entry in self.memor_events_frame.to_dict(orient='records'):
        #     self.logger.info(f"Processing event entry from gsheet: {event_entry}")
        #     person_numbers = event_entry['Personennummer'].split(", ")
        #     person_ids = []
        #     for person_id in person_numbers:
        #         person_ids.append(MemorStatics.PROJECT_ABBR + ".person." + str(person_id))
        #
        #     # split the categories by comma - BUT ignore commas within quotes (because of return from gsheets)
        #     person_categories = MemorProcessor.split_ignoring_quotes(event_entry['Kategorie'], ',')
        #
        #     cur_memor_event = MemorEvent(
        #         id=event_entry['Id'],
        #         title=event_entry['Titel'],
        #         person_ids=person_ids,
        #         type=event_entry['Typ'],
        #         description=event_entry['Beschreibung'],
        #         start_date=MemorProcessor._convert_date(event_entry['Startdatum']),
        #         end_date=MemorProcessor._convert_date(event_entry['Enddatum']),
        #         categories=person_categories,
        #         location=event_entry['Ort'],
        #         latt=event_entry['Längengrad'],
        #         long=event_entry['Breitengrad'])
        #
        #     self.logger.debug(f"Constructed memor event: {cur_memor_event}")
        #     self.memor_events.append(cur_memor_event)

        # for person in self.memor_persons:
        #     for event in self.memor_events:
        #         if person.id in event.person_ids:
        #             person.events.append(event)
        #             self.logger.debug(f"Linking person {person.id} to event {event.id}. Constructed memor person: {person}")
        #
        #     self.logger.info(f"Loaded memor person: {person}")

    def _load_metadata_csv(self, path: str):
        """
        Reads given file path as csv and returns a list of dictionary representing each row.
        Handles BOM, whitespace, and provides diagnostic logging.

        :param path: Path to the file that should be read
        :return: list of dictionaries representing each row. Key value is of head row.
        """
        rows = []
        if not os.path.exists(path):
            self.logger.info(f"No metadata file at {path} found!")
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

        rendered_persons = 0
        error_persons = 0

        for person in self.memor_persons:
            folder_name = person.id
            folder_path = os.path.join(MemorStatics.OUTPUT_DIR, str(folder_name))
            os.makedirs(folder_path, exist_ok=True)

            try:
                person.write_as_dublin_core()
                person.write_as_object_csv()
                # person.write_as_rdf_xml()
                person.write_as_turtle()
                person.write_as_search_json()
                person.write_as_image_files()
                person.write_as_document_files()
                person.write_as_geojson()
                person.write_as_datastreams_csv()
                self.logger.info(f"Outputted digital object: {folder_path}")
                rendered_persons += 1
            except Exception as e:
                logging.error(f"SKIPPING writing output files for memor person: {person.id} - Error writing digital object at path: {folder_path}: {e}")
                try:
                    shutil.rmtree(folder_path)
                    error_persons += 1
                except Exception as cleanup_error:
                    logging.error(f"Failed to remove folder {folder_path}: {cleanup_error}")

        logging.info(f"***** Finished writing individual persons as object folder. Successfully wrote: {rendered_persons} of {len(self.memor_persons)} persons as object folder")
        logging.info(f"***** Failed to write person as object folder count: {error_persons}")


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
    def map_gender_col(col_value) -> Literal["männlich", "weiblich"]:
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
        Extracts all unique victim categories from the memor persons
        :return: A set of unique victim categories
        """


        col = MemorProcessor.map_nullable_col(col)
        if col is None:
            logging.debug("No victim categories found in column")
            return []

        victim_categories = col.split(",")
        victim_categories = [cat.strip() for cat in victim_categories]

        # new
        sheet_internal_mapping = {
            "widerstand;politisch": "resistance-political",
            "widerstand;religiös": "resistance-religious",
            "widerstand;individuell": "resistance-individual",
            "widerstand;deserteure": "resistance-deserters",
            "zeugenjehovas": "witnesses-jehovah",
            "jüdischeopfer;jüdisch":"jewish-victims-jewish",
            "jüdischeopfer;als Jude verfolgt":"jewish-victims-persecuted-as-jew",
            "roma":"roma",
            "euthanasieopfer": "euthanasia-victim",
            "homosexuelleopfer": "homosexual-victim",
            "spanienkämpfer":"spain-fighter",
            "NS-Gegnerschaft":"ns-opposition"
        }

        victim_category_ids_mapped = []
        for victim_category in victim_categories:
            mapped_category_id = sheet_internal_mapping.get(victim_category, "MAPPING_ERROR")
            if mapped_category_id == "MAPPING_ERROR":
                msg = f"Invalid victim category '{victim_category}'"
                logging.error(msg)
                raise ValueError(msg)
            victim_category_ids_mapped.append(
                mapped_category_id
            )

        if len(victim_category_ids_mapped) == 0:
            logging.debug("No victim categories found in column")

        return victim_category_ids_mapped


    @staticmethod
    def map_memorial_signs(col):
        """
        Maps memorial signs from the column value
        """
        try:
            col = MemorProcessor.map_nullable_col(col)
            memorial_signs = col.split(";")
            memorial_signs = [sign.strip() for sign in memorial_signs]
            return memorial_signs
        except Exception as e:
            msg = f"Error analysing memorial signs. There might be no memorial signs assigned - assigning default empty list {e}"
            logging.warning(msg)
            return []


    def output_person_list_object(self):
        """
        Creates an object folder (with datastreams.csv / object.csv) containing all persons data
        as GEOJSON and an aggregated RDF Turtle file.
        """
        from rdflib import Graph
        from memorbuch_preprocessing.Person.memor_person_turtle_serialization import populate_person_graph, _bind_namespaces

        # first create folder
        object_id = "memor.person-register"
        folder_path = os.path.join(MemorStatics.OUTPUT_DIR, str(object_id))
        os.makedirs(folder_path, exist_ok=True)

        # ---------------------------------------------------------
        # 1. GEOJSON AGGREGATION
        # ---------------------------------------------------------
        all_features = []
        for person in self.memor_persons:
            person_features = person.to_geojson_features()
            all_features.extend(person_features)

        self.logger.info(f"Original feature count: {len(all_features)}")
        deduplicated_features = FeatureAggregator().deduplicate_geojson_features(all_features)
        self.logger.info(f"Deduplicated feature count: {len(deduplicated_features)}")

        geojson = {
            "type": "FeatureCollection",
            "vocab": MemorVocab.VOCAB_CONTAINER,
            "metadata": {
                "project": "MEMOR - Digitales Memorbuch",
                "total_persons": len(self.memor_persons),
                "total_location_events": len(deduplicated_features),
                "generated": datetime.now().isoformat()
            },
            "features": deduplicated_features
        }

        json_path = os.path.join(folder_path, 'EVENTS.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Outputted all persons GEOJSON object: {json_path}")

        # ---------------------------------------------------------
        # 2. RDF TURTLE AGGREGATION
        # ---------------------------------------------------------
        self.logger.info("Building aggregated RDF graph...")
        aggregated_graph = Graph()
        _bind_namespaces(aggregated_graph)

        for person in self.memor_persons:
            try:
                populate_person_graph(person, g=aggregated_graph)
            except Exception as e:
                self.logger.error(f"Failed to add person {person.id} to aggregated graph: {e}")

        aggregated_ttl_path = os.path.join(folder_path, "REGISTER.ttl")
        aggregated_graph.serialize(destination=aggregated_ttl_path, format="turtle", encoding="utf-8")
        self.logger.info(f"Outputted aggregated TTL: {aggregated_ttl_path}")

        # ---------------------------------------------------------
        # 3. METADATA (DC.xml & object.csv & datastreams.csv)
        # ---------------------------------------------------------
        dc_xml_string = f"""
            <oai_dc:dc xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                   xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd">
                <dc:identifier>{object_id}</dc:identifier>
                <dc:creator>Born digital - memor project GAMS</dc:creator>
                <dc:title xml:lang="de">Personenregister</dc:title>
                <dc:title xml:lang="en">person register and related indices</dc:title>
                <dc:subject>Register</dc:subject>
                <dc:rights>Creative Commons BY-NC 4.0</dc:rights>
                <dc:description xml:lang="de">Personenregister des Memor Projekts</dc:description>
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
            csv_writer.writerow([object_id, "Person register", "memor", "This digital object contains person registers and related indices for the MEMOR project", "Born digital - memor project GAMS", "Creative Commons BY-NC 4.0", "memor project GAMS5", "Memor datasheet transformed by Memor preprocessing tool", "Dataset", "EVENTS.json", "register"])
        self.logger.info(f"Outputted all persons object.csv: {object_csv_path}")

        # Datastreams csv
        datastreams_csv_path = os.path.join(folder_path, "datastreams.csv")
        with open(datastreams_csv_path, "w", encoding="utf-8", newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["dsid","dspath", "title","mimetype", "description","creator","rights"])
            csv_writer.writerow(["EVENTS.json","EVENTS.json","MEMOR person events geojson", "application/json", "GEOJSON file containing all MEMOR persons, associated events and locations.","Born digital - memor project GAMS","Creative Commons BY-NC 4.0"])
            csv_writer.writerow(["DC.xml","DC.xml", "Dublin Core Metadata","application/xml", "Dublin Core metadata for the persons register","Born digital - memor project GAMS","Creative Commons BY-NC 4.0"])
            csv_writer.writerow(["REGISTER.ttl", "REGISTER.ttl", "Aggregated Person Register", "text/turtle", "Aggregated RDF statements for all persons of the MEMOR project", "Born digital - memor project GAMS", "Creative Commons BY-NC 4.0"])
        self.logger.info(f"Outputted all persons datastreams.csv: {datastreams_csv_path}")