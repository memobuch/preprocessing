import os
from typing import Literal
from memobuch_preprocessing.MemoEvent import MemoEvent
import xml.etree.ElementTree as ET
from memobuch_preprocessing.MemoStatics import MemoStatics

class MemoPerson:
    def __init__(self, id: str, last_name: str, first_name: str, maiden_name: str, alternative_spelling: str, gender: Literal["male", "female"], is_youth: bool, memorial_sign: str, biography_text: str, event: MemoEvent = None):
        self.id = id
        self.last_name = last_name
        self.first_name = first_name
        self.maiden_name = maiden_name
        self.alternative_spelling = alternative_spelling
        self.gender = gender
        self.is_youth = is_youth
        self.memorial_sign = memorial_sign
        self.biography_text = biography_text
        self.event = event

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
        id_element.text = f"memo.{self.id}"

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

        dc_date = ET.SubElement(root, 'dc:date')
        dc_date.text = f"{self.event.start_date} - {self.event.end_date}"

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