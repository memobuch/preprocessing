import csv
import json
import os
from array import array
from typing import Literal
from memobuch_preprocessing.MemoEvent import MemoEvent
import xml.etree.ElementTree as ET
from memobuch_preprocessing.MemoStatics import MemoStatics
import pandas as pd

class MemoPerson:
    def __init__(self, id: str, last_name: str, first_name: str, maiden_name: str, alternative_spelling: str, gender: Literal["male", "female"], is_youth: bool, memorial_sign: str, biography_text: str, birth_place: str, birth_date: str,
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
        self.memorial_sign = memorial_sign
        self.biography_text = biography_text
        self.birth_place = birth_place
        self.birth_date = birth_date
        self.events = events

    def __repr__(self) -> str:
        return f"MemoPerson({self.id}, {self.last_name}, {self.first_name}, {self.maiden_name}, {self.alternative_spelling}, {self.gender}, {self.is_youth}, {self.memorial_sign}, {self.biography_text}, {str(self.events)})"


    def write_as_dublin_core(self):
        """
        Write the person as Dublin Core XML
        :return:
        """

        # logger.debug(f"Creating Dublin Core XML for digital object ID: memo.{entry['Identifikatornummer']}")
        root = ET.Element('oai_dc:dc', {'xmlns:dc': 'http://purl.org/dc/elements/1.1/', 'xmlns:oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/', 'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance', 'xsi:schemaLocation': 'http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd' })

        id_element = ET.SubElement(root, 'dc:identifier')
        id_element.text = self.id

        creator_element = ET.SubElement(root, 'dc:creator')
        creator_element.text = "Born digital - memo project GAMS"

        if self.first_name and self.last_name:
            title_element = ET.SubElement(root, 'dc:title', {'xml:lang': 'en'})
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

        dc_language = ET.SubElement(root, 'dc:language')
        dc_language.text = "de"

        dc_publisher = ET.SubElement(root, 'dc:publisher')
        dc_publisher.text = "Heimo Halbrainer (Hardcoded)"

        dc_rights = ET.SubElement(root, 'dc:rights')
        dc_rights.text = "Creative Commons BY-NC 4.0 (Hardcoded)"

        dc_rights2 = ET.SubElement(root, 'dc:rights')
        dc_rights2.text = "https://creativecommons.org/licenses/by-nc/4.0"

        dc_type = ET.SubElement(root, 'dc:type')
        dc_type.text = "Person"

        dc_format = ET.SubElement(root, 'dc:format')
        dc_format.text = "Born digital: Eintrag in google Tabelle"


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
        MEMO_BASE_URI = "http://digitales-memobuch.at/"
        MEMO_ONTOLOGY = MEMO_BASE_URI + "onotology#"


        rdf_ns = {'xmlns:rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'xmlns:dc': 'http://purl.org/dc/elements/1.1/', 'xmlns:foaf': 'http://xmlns.com/foaf/0.1/', 'xmlns:rdfs': 'http://www.w3.org/2000/01/rdf-schema#', 'xmlns:void': 'http://rdfs.org/ns/void#', 'xmlns:wgs84_pos': 'http://www.w3.org/2003/01/geo/wgs84_pos#', 'xmlns:memo': MEMO_ONTOLOGY}
        root = ET.Element('rdf:RDF', rdf_ns)
        description = ET.SubElement(root, 'rdf:Description', {'rdf:about': MEMO_BASE_URI + self.id})

        rdfs_label = ET.SubElement(description, 'rdfs:label')
        rdfs_label.text = f"{self.first_name} {self.last_name}"

        # rdf:type foaf:Person
        ET.SubElement(description, 'rdf:type', {'rdf:resource': 'http://xmlns.com/foaf/0.1/Person'})

        foaf_name = ET.SubElement(description, 'foaf:name')
        foaf_name.text = f"{self.first_name} {self.last_name}"

        foaf_family_name = ET.SubElement(description, 'foaf:familyName')
        foaf_family_name.text = self.last_name

        foaf_given_name = ET.SubElement(description, 'foaf:givenName')
        foaf_given_name.text = self.first_name

        if self.birth_place:
            foaf_based_near = ET.SubElement(description, 'foaf:based_near')
            foaf_based_near.text = self.birth_place

        if self.birth_date:
            foaf_birthday = ET.SubElement(description, 'foaf:birthday')
            foaf_birthday.text = self.birth_date



        for event in self.events:
            # add events as rdf model
            event_rdf_description = ET.SubElement(root, 'rdf:Description', {'rdf:about': MEMO_BASE_URI + self.id + "/events/" + str(event.id)})

            ET.SubElement(event_rdf_description, 'rdf:type', {'rdf:resource': 'http://digitales-memobuch.at/ontology#Event'})
            # type a wgs point
            ET.SubElement(event_rdf_description, 'rdf:type', {'rdf:resource': 'http://www.w3.org/2003/01/geo/wgs84_pos#Point'})

            ET.SubElement(event_rdf_description, 'wgs84_pos:lat', {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(event.latt)
            ET.SubElement(event_rdf_description, 'wgs84_pos:long', {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(event.long)

            event_rdf_creator = ET.SubElement(event_rdf_description, 'dc:creator')
            event_rdf_creator.text = "Born digital - memo project GAMS"

            rdfs_label = ET.SubElement(event_rdf_description, 'rdfs:label')
            rdfs_label.text = event.title

            event_dc_description = ET.SubElement(event_rdf_description, 'dc:description')
            event_dc_description.text = event.description

            event_start_date = ET.SubElement(event_rdf_description, 'memo:startDate')
            event_start_date.text = event.start_date

            event_end_date = ET.SubElement(event_rdf_description, 'memo:endDate')
            event_end_date.text = event.end_date

            for event_category_label in event.categories:
                event_category_elem = ET.SubElement(event_rdf_description, 'memo:category')
                event_category_elem.text = event_category_label

            event_location = ET.SubElement(event_rdf_description, 'memo:location')
            event_location.text = event.location

            event_creator = ET.SubElement(event_rdf_description, 'memo:creator')
            event_creator.text = "Born digital - memo project GAMS"

            event_rights = ET.SubElement(event_rdf_description, 'memo:rights')
            event_rights.text = "Creative Commons BY-NC 4.0"

            ET.SubElement(event_rdf_description, 'memo:describesPerson', {'rdf:resource': MEMO_BASE_URI + self.id})







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


    def write_as_search_json(self):
        """
        Write the person as search JSON

        """

        search_json_path = os.path.join(MemoStatics.OUTPUT_DIR, str(self.id), 'SEARCH.json')
        # TODO use gams specific fields
        data = {
            "id": self.id,
            "sys_entityTitle": f"{self.first_name} {self.last_name}",
            "sys_entityDesc": self.biography_text,
            # TODO could possibly use enums in SOLR!
            "sys_entityTypes": ["person"]
            # TODO think aboput keyword assigment
            # "keyword": self.memorial_sign,
        }

        death_event: MemoEvent = None
        for event in self.events:
            if event.type == "Tod":
                death_event = event
                break

        if death_event:
            # TODO add this start and end date ranges
            # data["sys_entityStartDateRanges"] = death_event.start_date
            # data["sys_entityEndDateRanges"] = death_event.end_date
            data["sys-entityLongLat"] = [death_event.latt, death_event.long]
            data["sys_entityTags"] = list(death_event.categories)
            data["sys-locationLabels"] =  [death_event.location]

        json_str = json.dumps(data, ensure_ascii=False, indent=4)

        with open(search_json_path, 'w', encoding='utf-8', newline="\n") as f:
            f.write(json_str)
