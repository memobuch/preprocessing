import csv
import os
from typing import Literal
from memobuch_preprocessing.MemoEvent import MemoEvent
import xml.etree.ElementTree as ET
from memobuch_preprocessing.MemoStatics import MemoStatics
import pandas as pd

class MemoPerson:
    def __init__(self, id: str, last_name: str, first_name: str, maiden_name: str, alternative_spelling: str, gender: Literal["male", "female"], is_youth: bool, memorial_sign: str, biography_text: str, birth_place: str, birth_date: str, events: list[MemoEvent] = []):
        self.id = id
        self.last_name = last_name
        self.first_name = first_name
        self.maiden_name = maiden_name
        self.alternative_spelling = alternative_spelling
        self.gender = gender
        self.is_youth = is_youth
        self.memorial_sign = memorial_sign
        self.biography_text = biography_text
        self.birth_place = birth_place
        self.birth_date = birth_date
        self.events = events

    def __repr__(self) -> str:
        return f"MemoPerson({self.id}, {self.last_name}, {self.first_name}, {self.maiden_name}, {self.alternative_spelling}, {self.gender}, {self.is_youth}, {self.memorial_sign}, {self.biography_text})"


    def write_as_dublin_core(self):
        """
        Write the person as Dublin Core XML
        :return:
        """

        # logger.debug(f"Creating Dublin Core XML for digital object ID: memo.{entry['Identifikatornummer']}")
        root = ET.Element('dublin_core', {'xmlns:dc': 'http://purl.org/dc/elements/1.1/'})

        id_element = ET.SubElement(root, 'dc:identifier')
        id_element.text = self.id

        creator_element = ET.SubElement(root, 'dc:creator')
        creator_element.text = "Born digital - memo project GAMS"

        if self.first_name and self.last_name:
            title_element = ET.SubElement(root, 'dc:title', {'lang': 'en'})
            title_element.text = f"{self.first_name} {self.last_name}"

        if self.is_youth:
            subject_element = ET.SubElement(root, 'dc:subject')
            subject_element.text = 'jugendlich'

        rights_element = ET.SubElement(root, 'dc:rights')
        rights_element.text = "Creative Commons BY-NC 4.0"

        description_element = ET.SubElement(root, 'dc:description', {'lang': 'de'})
        description_element.text = self.biography_text

        relation_element = ET.SubElement(root, 'dc:relation')
        relation_element.text = self.memorial_sign

        date_element = ET.SubElement(root, 'dc:date')
        date_element.text = self.birth_date

        # TODO - tricky! must look for the geburts-event
        # dc_date = ET.SubElement(root, 'dc:date')
        # dc_date.text = f"{self.event.start_date} - {self.event.end_date}"

        dc_language = ET.SubElement(root, 'dc:language')
        dc_language.text = "de"

        dc_publisher = ET.SubElement(root, 'dc:publisher')
        dc_publisher.text = "Heimo Halbrainer (Hardcoded)"

        dc_rights = ET.SubElement(root, 'dc:rights')
        dc_rights.text = "Creative Commons BY-NC 4.0 (Hardcoded)"

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
        object_csv_path = os.path.join(MemoStatics.OUTPUT_DIR,  str(self.id), 'object.csv')
        data = {
            'recid': [self.id],
            'title': [f"{self.first_name} {self.last_name}"],
            'project': [MemoStatics.PROJECT_ABBR],
            'description': [self.biography_text],
            'creator': ["Born digital - memo project GAMS"],
            'rights': ['Creative Commons BY-NC 4.0'],
            'publisher': ['memo project GAMS5'],
            'source': ['Demo source'],
            'objectType': ['RDF']
        }

        df = pd.DataFrame(data)
        df.to_csv(object_csv_path, index=False, sep=',', quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8', lineterminator='\n')
        # logger.info(f"Created object CSV at: {object_csv_path}")


    def write_as_rdf_xml(self):
        """
        RDF.xml file per object that contains the dc elements in RDF format AND the rest of the information
        provided by the source csv file.
        :param entry:
        :param folder_path:
        :return:
        """
        # logger.debug(f"Creating RDF XML for digital object ID: memo.{entry['Identifikatornummer']}")
        rdf_ns = {'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'dc': 'http://purl.org/dc/elements/1.1/', 'foaf': 'http://xmlns.com/foaf/0.1/'}
        root = ET.Element('rdf:RDF', rdf_ns)
        description = ET.SubElement(root, 'rdf:Description', {'rdf:about': self.id})

        creator_element = ET.SubElement(description, 'dc:creator')
        creator_element.text = "Born digital - memo project GAMS"

        identifier_element = ET.SubElement(description, 'dc:identifier')
        identifier_element.text = str(self.id)

        rights_element = ET.SubElement(description, 'dc:rights')
        rights_element.text = "Creative Commons BY-NC 4.0"

        #
        xml_file_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id), 'RDF.xml')
        tree = ET.ElementTree(root)
        tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)

        return root


    def write_as_datastreams_csv(self):
        folder_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id))
        datastreams_csv_path = os.path.join(folder_path, 'datastreams.csv')
        datastreams = []

        # TODO think about: method must be called last in the chain!

        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path) and item != 'object.csv':
                datastream = {
                    'dsid': item,
                    'dspath': item,
                    'title': item,
                    'mimetype': 'application/xml' if item.endswith('.xml') else 'text/plain',
                    'description': f'Datastream for {item}',
                    'creator': 'Born digital - memo project GAMS',
                    'rights': 'Creative Commons BY-NC 4.0',
                    # 'size': os.path.getsize(item_path)
                }
                datastreams.append(datastream)

        df = pd.DataFrame(datastreams)
        df.to_csv(datastreams_csv_path, index=False, sep=',', quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8', lineterminator='\n')
        # logger.info(f"Created datastreams CSV at: {datastreams_csv_path}")