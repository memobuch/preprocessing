import csv
import json
import mimetypes
import os
import shutil
from typing import Literal
from memobuch_preprocessing.MemoEvent import MemoEvent
import xml.etree.ElementTree as ET
from memobuch_preprocessing.MemoStatics import MemoStatics
import pandas as pd

from memobuch_preprocessing.Person.MemoPersonFile import MemoPersonFile


class MemoPerson:

    images: list[MemoPersonFile]
    documents: list[MemoPersonFile]

    def __init__(self, id: str, last_name: str, first_name: str, maiden_name: str, alternative_spelling: str, gender: Literal["male", "female"], is_youth: bool, memorial_sign: str, biography_text: str, birth_place: str, birth_date: str, death_place: str, death_longitude: float, death_lattitude: float, voluntary_address: str, voluntary_longitude: float, voluntary_latitude: float, forced_address: str, forced_longitude: float, forced_latitude: float, victim_category: list[str], literature: str,
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

        self.death_place = death_place
        self.death_longitude = death_longitude
        self.death_latitude = death_lattitude

        self.voluntary_address = voluntary_address
        self.voluntary_longitude = voluntary_longitude
        self.voluntary_latitude = voluntary_latitude

        self.forced_address = forced_address
        self.forced_longitude = forced_longitude
        self.forced_latitude = forced_latitude

        self.victim_category = victim_category
        self.literature = literature

        # images assigned to a memo person
        self.images = []
        # memo documents
        self.documents = []

    def __repr__(self) -> str:
        return f"MemoPerson(id={self.id}, last_name={self.last_name}, first_name={self.first_name}, maiden_name={self.maiden_name}, alternative_spelling={self.alternative_spelling}, gender={self.gender}, is_youth={self.is_youth}, memorial_sign={self.memorial_sign}, biography_text={self.biography_text}, birth_place={self.birth_place}, birth_date={self.birth_date}, death_place={self.death_place}, death_longitude={self.death_longitude}, death_latitude={self.death_latitude}, voluntary_address={self.voluntary_address}, voluntary_longitude={self.voluntary_longitude}, voluntary_latitude={self.voluntary_latitude}, forced_address={self.forced_address}, forced_longitude={self.forced_longitude}, forced_latitude={self.forced_latitude}, victim_category={self.victim_category}, literature={self.literature}, images={self.images}, events={self.events}, documents={self.documents})"

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
        description = ET.SubElement(root, 'rdf:Description', {'rdf:about': MEMO_BASE_URI + "persons/" + self.id})

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

        # handling of images
        for i, image in enumerate(self.images):
            # TODO here the correct dsid is needed from the datastream.csv!
            image_dsid =  os.path.basename(image.source_path).upper()
            if i == 0:
                ET.SubElement(description, 'memo:portraitImage', {'rdf:resource': f'http://localhost:18085/api/v1/projects/memo/objects/memo.person.3/datastreams/{image_dsid}'})
            else:
                ET.SubElement(description, 'memo:hasHistoricImage', {'rdf:resource': f'http://localhost:18085/api/v1/projects/memo/objects/memo.person.3/datastreams/{image_dsid}'})
                pass

        # handling of documents
        for i, document in enumerate(self.documents):
            # TODO the correct dsid should come from the datastream.csv!
            document_dsid = os.path.basename(document.source_path).upper()
            ET.SubElement(description, 'memo:hasHistoricSourceDocument', {'rdf:resource': f'http://localhost:18085/api/v1/projects/memo/objects/memo.person.3/datastreams/{document_dsid}'})

        for event in self.events:
            # add events as rdf model
            event_rdf_description = ET.SubElement(root, 'rdf:Description', {'rdf:about': MEMO_BASE_URI + "persons/" + self.id + "/events/" + str(event.id)})

            ET.SubElement(event_rdf_description, 'rdf:type', {'rdf:resource': 'http://digitales-memobuch.at/ontology#Event'})
            # type a wgs point
            ET.SubElement(event_rdf_description, 'rdf:type', {'rdf:resource': 'http://www.w3.org/2003/01/geo/wgs84_pos#Point'})

            ET.SubElement(event_rdf_description, 'wgs84_pos:lat', {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(event.lat)
            ET.SubElement(event_rdf_description, 'wgs84_pos:long', {'rdf:datatype': 'http://www.w3.org/2001/XMLSchema#float'}).text = str(event.long)

            event_rdf_creator = ET.SubElement(event_rdf_description, 'dc:creator')
            event_rdf_creator.text = "Born digital - memo project GAMS"

            rdfs_label = ET.SubElement(event_rdf_description, 'rdfs:label')
            rdfs_label.text = event.title

            event_dc_description = ET.SubElement(event_rdf_description, 'dc:description')
            event_dc_description.text = event.description

            event_date = ET.SubElement(event_rdf_description, 'memo:date')
            event_date.text = event.date

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
                    msg = f"Mimetype from file at path {item_path} is unexpectedly None!"
                    raise ValueError(msg)

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
                if "image" in mimetype :
                    # name of the generated datastream file
                    output_file_name = os.path.basename(item_path)
                    for image in self.images:
                        # file name stored in MemoPersonImage instance
                        image_file_name = os.path.basename(image.source_path)
                        if output_file_name == image_file_name:
                            datastream["title"] = image.title
                            datastream["description"] = image.desc

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
            "entityTitle": f"{self.first_name} {self.last_name}",
            "entityDesc": self.biography_text,
            # TODO could possibly use enums in SOLR!
            "entityTypes": ["person"],
            # TODO think aboput keyword assigment
            # "keyword": self.memorial_sign,
            "entityStartDate": self.birth_date,
            "entityPointers": [self.memorial_sign]
        }

        death_event: MemoEvent = None
        for event in self.events:
            if event.type == "Tod":
                death_event = event
                break

        if death_event:
            data["entityLongLat"] = f"{death_event.long}, {death_event.latt}"
            data["entityTags"] = list(death_event.categories)
            data["entityLocationLabels"] =  [death_event.location]
            data["entityEndDate"] = death_event.end_date

        json_str = json.dumps(data, ensure_ascii=False, indent=4)

        with open(search_json_path, 'w', encoding='utf-8', newline="\n") as f:
            f.write(json_str)
