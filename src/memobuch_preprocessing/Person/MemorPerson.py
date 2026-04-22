import csv
import json
import logging
import math
import mimetypes
import os
import shutil
from datetime import datetime
from typing import Literal
from memobuch_preprocessing.MemorEvent import MemoEvent
import xml.etree.ElementTree as ET
from memobuch_preprocessing.MemorStatics import MemoStatics
import pandas as pd

from memobuch_preprocessing.MemorVocab import MemoVocab
from memobuch_preprocessing.Person.MemorPersonFile import MemoPersonFile
from memobuch_preprocessing.Person.memo_person_rdf_serialization import write_as_rdf_xml_improved
from memobuch_preprocessing.Person.memo_person_turtle_serialization import write_as_turtle

class MemoPerson:
    images: list[MemoPersonFile]
    documents: list[MemoPersonFile]

    def __init__(self, id: str, last_name: str | None, first_name: str | None, maiden_name: str | None, alternative_spelling: str |None,
                 gender: Literal["male", "female"], is_youth: bool, memorial_signs: list[str], biography_text: str | None,
                 birth_place: str | None, birth_date: str | None, death_date: str | None, death_place: str | None, death_longitude: float | None,
                 death_lattitude: float | None, voluntary_address: str | None, voluntary_longitude: float | None, voluntary_latitude: float | None,
                 forced_address: str | None, forced_longitude: float | None, forced_latitude: float | None, victim_category: list[str],
                 literature: str | None,
                 events=None):

        if events is None:
            events = []

        self.id = id
        self.last_name = last_name
        self.first_name = first_name
        self.maiden_name = maiden_name
        self.alternative_spelling = alternative_spelling
        self.gender = gender
        self.is_youth = is_youth
        self.memorial_signs = memorial_signs
        self.biography_text = biography_text
        self.birth_place = birth_place
        self.birth_date = birth_date
        self.death_date = death_date
        self.events = events

        # geographical death place
        self.death_place = death_place
        self.death_longitude = death_longitude
        self.death_latitude = death_lattitude
        # geographical voluntary address
        self.voluntary_address = voluntary_address
        self.voluntary_longitude = voluntary_longitude
        self.voluntary_latitude = voluntary_latitude
        # geographical forced address
        self.forced_address = forced_address
        self.forced_longitude = forced_longitude
        self.forced_latitude = forced_latitude

        self.victim_category = victim_category
        self.literature = literature

        # images assigned to a memo person
        self.images = []
        # memo documents
        self.documents = []

        self.validate()

    def __repr__(self) -> str:
        return f"MemoPerson(id={self.id}, last_name={self.last_name}, first_name={self.first_name}, maiden_name={self.maiden_name}, alternative_spelling={self.alternative_spelling}, gender={self.gender}, is_youth={self.is_youth}, memorial_sign={self.memorial_signs}, biography_text={self.biography_text}, birth_place={self.birth_place}, birth_date={self.birth_date}, death_place={self.death_place}, death_longitude={self.death_longitude}, death_latitude={self.death_latitude}, voluntary_address={self.voluntary_address}, voluntary_longitude={self.voluntary_longitude}, voluntary_latitude={self.voluntary_latitude}, forced_address={self.forced_address}, forced_longitude={self.forced_longitude}, forced_latitude={self.forced_latitude}, victim_category={self.victim_category}, literature={self.literature}, images={self.images}, events={self.events}, documents={self.documents})"

    def add_image(self, image: MemoPersonFile):
        self.images.append(image)

    def add_document(self, document: MemoPersonFile):
        self.documents.append(document)

    def add_event(self, event: MemoEvent):
        self.events.append(event)

    def write_as_dublin_core(self):
        """
        Write the person as Dublin Core XML
        :return:
        """

        # logger.debug(f"Creating Dublin Core XML for digital object ID: memo.{entry['Identifikatornummer']}")
        root = ET.Element('oai_dc:dc', {'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
                                        'xmlns:oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
                                        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                                        'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd'})

        id_element = ET.SubElement(root, 'dc:identifier')
        id_element.text = self.id

        creator_element = ET.SubElement(root, 'dc:creator')
        creator_element.text = "Heimo Halbrainer"

        creator_element2 = ET.SubElement(root, 'dc:creator')
        creator_element2.text = "Gerald Lamprecht"

        if self.first_name and self.last_name:
            title_element = ET.SubElement(root, 'dc:title', {'xml:lang': 'en'})
            title_element.text = f"{self.first_name} {self.last_name} (person description)"

        if self.is_youth:
            subject_element = ET.SubElement(root, 'dc:subject')
            subject_element.text = 'jugendliche Opfer' # TODO should be english

        for category in self.victim_category:
            subject_element = ET.SubElement(root, 'dc:subject')
            subject_element.text = self.map_dublin_core_subject_id_to_label(category) # TODO english

        rights_element = ET.SubElement(root, 'dc:rights', {'xml:lang': 'en'})
        rights_element.text = "Creative Commons BY-NC 4.0"

        description_element = ET.SubElement(root, 'dc:description', {'xml:lang': 'de'})
        description_element.text = self.biography_text

        date_element = ET.SubElement(root, 'dc:date')
        date_element.text = "2026"

        dc_language = ET.SubElement(root, 'dc:language')
        dc_language.text = "de"

        dc_publisher = ET.SubElement(root, 'dc:publisher', {'xml:lang': 'de'})
        dc_publisher.text = "GAMS"

        dc_rights2 = ET.SubElement(root, 'dc:rights')
        dc_rights2.text = "https://creativecommons.org/licenses/by-nc/4.0"

        dc_type = ET.SubElement(root, 'dc:type', {'xml:lang': 'en'})
        dc_type.text = "Dataset"

        # makes no sense in MEMO's case
        dc_format = ET.SubElement(root, 'dc:format')
        dc_format.text = "RDF dataset"

        dc_relation_memo = ET.SubElement(root, 'dc:relation')
        dc_relation_memo.text = "https://ns-opfer-graz.at"

        for derla_sign in self.memorial_signs:
            dc_relation = ET.SubElement(root, 'dc:relation')
            dc_relation.text = f"https://gams.uni-graz.at/{derla_sign}"

        # logger.info(f"Created Dublin Core XML for digital object ID: memo.{entry['Identifikatornummer']}")
        xml_file_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id), 'DC.xml')
        tree = ET.ElementTree(root)
        tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)
        # self.logger.info(f"Created XML file at: {xml_file_path}")

    def write_as_object_csv(self):
        """
        Write the person as object CSV
        :return:
        """
        # logger.debug(f"Creating object CSV for digital object ID: memo.{entry['Identifikatornummer']}")
        object_csv_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id), 'object.csv')

        object_tags = []
        for category in self.victim_category:
            object_tags.append(category)

        if self.is_youth:
            object_tags.append("jugendlich")

        object_tags.append("person")
        object_tags.append(self.gender)

        data = {
            'recid': [self.id],
            'title': [f"{self.first_name} {self.last_name} (person description)"],
            'project': [MemoStatics.PROJECT_ABBR],
            'description': [self.biography_text],
            'creator': ["Heimo Halbrainer;Gerald Lamprecht"],
            'rights': ['Creative Commons BY-NC 4.0'],
            'publisher': ['GAMS'],
            "funder": ";".join(["City of Graz", "National Fund of the Republic of Austria for Victims of National Socialism", "Future Fund of the Republic of Austria", "Federal Chancellery of the Republic of Austria"]),
            'source': ['Memo datasheet transformed by Memo preprocessing tool'],
            'objectType': ['RDF'],
            'mainResource': ['RDF.xml'],
            'tags': ";".join(object_tags) # tags separated by semicolon # TODO make sure english translation?
        }

        df = pd.DataFrame(data)
        df.to_csv(object_csv_path, index=False, sep=',', quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8',
                  lineterminator='\n')
        # logger.info(f"Created object CSV at: {object_csv_path}")

    def write_as_rdf_xml(self):
        return write_as_rdf_xml_improved(self)

    def write_as_image_files(self):
        """
        Copies all related images to the person's output folder
        :return: 
        """
        folder_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id))
        if not os.path.exists(folder_path):
            msg = f"Expected output folder not existent at path: {folder_path}"
            raise ValueError(msg)

        for memo_image in self.images:
            source_path = memo_image.source_path
            target_path = os.path.join(folder_path, os.path.basename(source_path))
            if os.path.isfile(source_path):
                shutil.copyfile(source_path, target_path)
            else:
                msg = f"Image copying: File at path {source_path} does not exist!"
                raise ValueError(msg)

    def write_as_document_files(self):
        """
        Copies all related documents to the person's output folder
        :return:
        """
        folder_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id))
        if not os.path.exists(folder_path):
            msg = f"Expected output folder not existent at path: {folder_path}"
            raise ValueError(msg)

        for memo_document in self.documents:
            # TODO maybe define a substructure, like /documents?
            source_path = memo_document.source_path
            target_path = os.path.join(folder_path, os.path.basename(source_path))
            if os.path.isfile(source_path):
                shutil.copyfile(source_path, target_path)
            else:
                msg = f"Document copying: File at path {source_path} does not exist!"
                raise ValueError(msg)

    def write_as_datastreams_csv(self):
        folder_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id))
        datastreams_csv_path = os.path.join(folder_path, 'datastreams.csv')
        datastreams = []

        # TODO think about: method must be called last in the chain!

        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path) and item != 'object.csv':
                mimetype = mimetypes.guess_type(item_path)[0]
                if mimetype is None:
                    # turtle might not be recognized
                    if item.endswith('.ttl'):
                        mimetype = 'text/turtle'
                    else:
                        msg = f"Mimetype from file at path {item_path} is unexpectedly None!"
                        raise ValueError(msg)

                # skip datastreams.csv itself
                if item == "datastreams.csv":
                    continue

                datastream = {
                    'dsid': item,
                    'dspath': item,
                    'title': item,
                    'mimetype': mimetype,
                    'description': f'Datastream for {item}',
                    'creator': 'Born digital - memo project GAMS',
                    'rights': 'Creative Commons BY-NC 4.0',
                    # 'size': os.path.getsize(item_path)
                }

                # if image apply metadata and image
                if "image" in mimetype:
                    # name of the generated datastream file
                    output_file_name = os.path.basename(item_path)
                    for image in self.images:
                        # file name stored in MemoPersonImage instance
                        image_file_name = os.path.basename(image.source_path)
                        if output_file_name == image_file_name:
                            datastream["title"] = image.title
                            datastream["description"] = f"{image.desc} | {image.source}"

                # Apply metadata to memo documents (for datastreams.csv)
                if "image" not in mimetype:
                    output_file_name = os.path.basename(item_path)
                    for document in self.documents:
                        document_file_name = os.path.basename(document.source_path)
                        if output_file_name == document_file_name:
                            datastream["title"] = document.title
                            datastream["description"] = document.desc

                datastreams.append(datastream)

        df = pd.DataFrame(datastreams)
        df.to_csv(datastreams_csv_path, index=False, sep=',', quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8',
                  lineterminator='\n')
        # logger.info(f"Created datastreams CSV at: {datastreams_csv_path}")

    def write_as_turtle(self):
        """Write SEMANTIC_STATEMENTS.ttl for GAMS5 triple store integration."""
        return write_as_turtle(self)

    def write_as_search_json(self):
        """
        Write the person as search JSON

        """

        tags = ["person"]
        # add victim categories as tags
        for category in self.victim_category:
            tags.append(category)

        if self.is_youth:
            tags.append("jugendlich")

        search_json_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id), 'CUSTOM_SEARCH.json')
        data = [{
            # first required fields
            "id": self.id,
            "objectId": self.id,  # same in case of memo
            "objectProjectAbbr": "memo",
            "entityTitles": [f"{self.first_name} {self.last_name}"],
            "entityFulltext": self.biography_text,
            "entityTags": tags,
            "entityStartDate": MemoPerson._convert_date(self.birth_date),
            "entityEndDate": self.death_date,
            "entityPointers": [self.memorial_signs]
        }]

        # temporary testing purpose:
        # additionally create 100 randomized dictionary to data array
        for i in range(1000):
            random_name = f"{self.first_name}_extra_{i} {self.last_name}_extra_{i}"
            random_description = f"{self.first_name} {self.last_name}_extra_{i}"
            data.append({
                "id": f"{self.id}_extra_{i}",
                "objectId": self.id,
                "objectProjectAbbr": "memo",
                "entityTitles": [random_name],
                "entityFulltext": random_description,
                "entityTags": tags,
                # "entityStartDate": self.birth_date,
                "entityPointers": [self.memorial_signs]
            })

        death_event: MemoEvent = None
        for event in self.events:
            if event.type == "Tod":
                death_event = event
                break

        if death_event:
            data["entityLongLat"] = f"{death_event.long}, {death_event.latt}"
            data["entityTags"] = list(death_event.categories)
            data["entityLocationLabels"] = [death_event.location]
            data["entityEndDate"] = death_event.end_date

        json_str = json.dumps(data, ensure_ascii=False, indent=4)

        with open(search_json_path, 'w', encoding='utf-8', newline="\n") as f:
            f.write(json_str)

    def validate(self):
        """

        """
        # validate id
        if 'nan' in self.id.lower():
            msg = f"Person ID cannot contain 'nan'. At person: {self}"
            logging.error(msg)
            raise ValueError(msg)

    @staticmethod
    def datetime_valid(dt_str: str):
        try:
            datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return False
        return True

    @staticmethod
    def _convert_date(date: str):
        """
        Converts a date from the format dd.mm.yyyy to the format yyyy-mm-dd
        :param date: The date to convert
        :return: The converted date
        """

        try:
            day, month, year = date.split('.')
            built_date = f"{year}-{month}-{day}T00:00:00Z"

            # constructed must parse as ISO 8601 date
            if MemoPerson.datetime_valid(built_date):
                return built_date
            else:
                raise ValueError(f"Invalid date format after conversion: {built_date}")

        except Exception as e:
            logging.debug(f"Invalid date format - assigning default value: {date} {e}")
            # TODO assign some default date?
            return "2015-09-01T00:00:00Z"

    def map_dublin_core_subject_id_to_label(self, dc_field: str) -> str:
        """
        Maps a Dublin Core subject id to a human-readable label
        :param dc_field: The Dublin Core field
        :return: The human-readable label
        """

        # small error safe for nan values
        mapping = MemoVocab.VICTIM_CATEGORY_TYPES

        dc_field_mapped = mapping.get(dc_field)

        if dc_field_mapped is None:
            msg = f"Mapping for Dublin Core field '{dc_field}' resulted in None. At person: {self}"
            logging.error(msg)
            raise ValueError(msg)

        mapped = dc_field_mapped.get("label")

        if mapped is None:
            msg = f"Mapping for Dublin Core field '{dc_field}' and extracting the label resulted in None. At person: {self}"
            logging.error(msg)
            raise ValueError(msg)

        return mapped


    def to_geojson_features(self) -> list[dict]:
        """
        Convert all biographical location events to GeoJSON Feature objects.

        Returns a list of GeoJSON Feature dicts, where each feature represents
        a specific event in the person's life with geographical coordinates.

        Event types: birth, voluntary_residence, forced_residence,
                     imprisonment, flight, death

        Returns:
            list[dict]: List of GeoJSON Feature dictionaries
        """
        features = []

        # Helper to create a feature
        def create_feature(event_type: str, lon: float, lat: float,
                           place_name: str, date: str = None,
                           event_id: str = None, title: str = None,
                           description: str = None) -> dict | None:
            """Create a GeoJSON feature with standardized properties."""

            if lon is None or lat is None:
                return None  # Skip if no coordinates

            # Skip if coordinates are NaN
            if math.isnan(float(lon)) or math.isnan(float(lon)):
                return None

            # Build person name
            person_name = f"{self.first_name or ''} {self.last_name or ''}".strip()

            # build tags associated with an event (contains victim categories AND event types)
            feature_tags = [event_type]
            for category in self.victim_category:
                feature_tags.append(category)

            # Create base feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)]  # [lng, lat] - GeoJSON standard!
                },
                "properties": {
                    # Core identification
                    "person_id": self.id,
                    "person_name": person_name,
                    "tags": feature_tags,
                    # "event_type": event_type,
                    # "event_type_label": config.get('label_de', event_type),

                    # Location details
                    "place_name": place_name,
                    "date": date,

                    # Person context
                    "birth_date": self.birth_date,
                    "death_date": self.death_date,
                    "gender": self.gender,
                    "is_youth": self.is_youth,
                    # "victim_categories": self.victim_category,
                }
            }

            # Add optional event-specific data
            if event_id:
                feature["properties"]["event_id"] = event_id
            if title:
                feature["properties"]["event_title"] = title
            if description:
                feature["properties"]["event_description"] = description

            return feature

        # =========================================================================
        # 1. BIRTH EVENT
        # =========================================================================
        # NOTE: Currently birth_place has no coordinates in data model!
        if self.birth_place:
            pass

        # =========================================================================
        # 2. VOLUNTARY RESIDENCE EVENT
        # =========================================================================
        if self.voluntary_address and self.voluntary_longitude and self.voluntary_latitude:
            voluntary_feature = create_feature(
                event_type='voluntary_residence',
                lon=self.voluntary_longitude,
                lat=self.voluntary_latitude,
                place_name=self.voluntary_address,
                date=None  # Usually no specific date for residence
            )
            if voluntary_feature:
                features.append(voluntary_feature)

        # =========================================================================
        # 3. FORCED RESIDENCE EVENT
        # =========================================================================
        if self.forced_address and self.forced_longitude and self.forced_latitude:
            forced_feature = create_feature(
                event_type='forced_residence',
                lon=self.forced_longitude,
                lat=self.forced_latitude,
                place_name=self.forced_address,
                date=None  # Date might be in biography or unknown
            )
            if forced_feature:
                features.append(forced_feature)

        # =========================================================================
        # 4. IMPRISONMENT & FLIGHT EVENTS (from MemoEvent objects)
        # =========================================================================
        for event in self.events:
            if event.lat is not None and event.long is not None:
                # Map MemoEvent.type to our unified event types
                event_type_map = {
                    'haft': 'imprisonment',
                    'flucht': 'flight'
                }

                unified_type = event_type_map.get(event.type, event.type)

                event_feature = create_feature(
                    event_type=unified_type,
                    lon=event.long,
                    lat=event.lat,
                    place_name=event.location,
                    date=event.date,
                    event_id=event.id,
                    title=event.title,
                    description=event.description
                )
                if event_feature:
                    features.append(event_feature)

        # =========================================================================
        # 5. DEATH EVENT
        # =========================================================================
        if self.death_place and self.death_longitude and self.death_latitude:
            death_feature = create_feature(
                event_type='death',
                lon=self.death_longitude,
                lat=self.death_latitude,
                place_name=self.death_place,
                date=self.death_date
            )
            if death_feature:
                features.append(death_feature)

        return features


    def write_as_geojson(self):
        """
        Write person's location events as a GeoJSON FeatureCollection file.
        Output: {OUTPUT_DIR}/{person_id}/LOCATIONS.json
        """
        features = self.to_geojson_features()

        if not features:
            # No geographical data available
            return

        geojson = {
            "type": "FeatureCollection",
            "vocab": MemoVocab.VOCAB_CONTAINER,
            "metadata": {
                "person_id": self.id,
                "person_name": f"{self.first_name} {self.last_name}",
                "birth_date": self.birth_date,
                "death_date": self.death_date,
                # "victim_categories": self.victim_category,
                "is_youth": self.is_youth,
                "gams_link": f"https://gams.uni-graz.at/o:{self.id}",
                "feature_count": len(features),
                # "event_types": list(set(f['properties']['event_type'] for f in features))
            },
            "features": features
        }

        # Write to file
        from memobuch_preprocessing.MemorStatics import MemoStatics
        json_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id), 'EVENTS.json')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)

        return json_path