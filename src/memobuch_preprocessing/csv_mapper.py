import csv
import pandas as pd
import os
import xml.etree.ElementTree as ET
import logging

# Script to create folders and files for digital objects to be created on GAMS5
# Each folder to be created represents a digital object to be created on GAMS5 (as REST-API) (Geisteswissenschaftliches Asset Management Systems)
# each file inside the folder will be a datastream (Except the object.csv file, which is metadata for a digital object)
# The id extracted from the csv files are being used to create the digital object's id, like memo.1
# The GAMS-REST-API has projects, named 'memo' in our case that will contain the digital objects

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_output_folder(output_root):
    logger.debug(f"Clearing output folder: {output_root}")
    for item in os.listdir(output_root):
        item_path = os.path.join(output_root, item)
        if os.path.isfile(item_path) and item != 'README.md':
            os.remove(item_path)
            logger.info(f"Deleted file: {item_path}")
        elif os.path.isdir(item_path):
            for root, dirs, files in os.walk(item_path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                    logger.info(f"Deleted file: {os.path.join(root, name)}")
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
                    logger.info(f"Deleted directory: {os.path.join(root, name)}")
            os.rmdir(item_path)
            logger.info(f"Deleted directory: {item_path}")

def create_dublin_core_xml(entry):
    logger.debug(f"Creating Dublin Core XML for digital object ID: memo.{entry['Identifikatornummer']}")
    root = ET.Element('dublin_core', {'xmlns:dc': 'http://purl.org/dc/elements/1.1/'})
    mapping = {
        'Geschlecht': 'subject',
        'Freitext / Biografie': 'description'
    }

    for csv_column, dc_element in mapping.items():
        if entry[csv_column]:
            element = ET.SubElement(root, f'dc:{dc_element}')
            element.text = str(entry[csv_column])
            logger.debug(f"Added element: dc:{dc_element} with text: {entry[csv_column]}")

    creator_element = ET.SubElement(root, 'dc:creator')
    creator_element.text = "Born digital - memo project GAMS"

    if entry['Vorname'] and entry['Nachname']:
        title_element = ET.SubElement(root, 'dc:title', {'lang': 'en'})
        title_element.text = f"{entry['Vorname']} {entry['Nachname']}"

    if entry['Jugendlich'] == 'ja':
        subject_element = ET.SubElement(root, 'dc:subject')
        subject_element.text = 'jugendlich'

    identifier_element = ET.SubElement(root, 'dc:identifier')
    identifier_element.text = f"memo.{entry['Identifikatornummer']}"

    rights_element = ET.SubElement(root, 'dc:rights')
    rights_element.text = "Creative Commons BY-NC 4.0"

    logger.info(f"Created Dublin Core XML for digital object ID: memo.{entry['Identifikatornummer']}")
    return root

def create_object_csv(entry, folder_path):
    logger.debug(f"Creating object CSV for digital object ID: memo.{entry['Identifikatornummer']}")
    object_csv_path = os.path.join(folder_path, 'object.csv')
    data = {
        'recid': [f"memo.{entry['Identifikatornummer']}"],
        'title': [f"{entry['Vorname']} {entry['Nachname']}"],
        'project': ['memo'],
        'description': [entry['Freitext / Biografie']],
        'creator': ['Born digital - memo project GAMS'],
        'rights': ['Creative Commons BY-NC 4.0'],
        'publisher': [''],
        'source': [''],
        'object_type': ['']
    }

    df = pd.DataFrame(data)
    df.to_csv(object_csv_path, index=False, sep=',', quotechar='"', quoting=csv.QUOTE_ALL, encoding='utf-8')
    logger.info(f"Created object CSV at: {object_csv_path}")

def main():
    output_root = 'output'
    os.makedirs(output_root, exist_ok=True)
    clear_output_folder(output_root)

    df = pd.read_csv('data' + os.path.sep + 'memobuch_demodata.csv', sep=';')
    demo_dict = df.to_dict(orient='records')
    logger.info(f"Loaded data from memobuch_demodata.csv with {len(demo_dict)} entries")

    for entry in demo_dict:
        folder_name = f"memo.{entry['Identifikatornummer']}"
        folder_path = os.path.join(output_root, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        logger.debug(f"Created folder for digital object: {folder_path}")

        xml_root = create_dublin_core_xml(entry)
        xml_file_path = os.path.join(folder_path, 'DC.xml')
        tree = ET.ElementTree(xml_root)
        tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)
        logger.info(f"Created XML file at: {xml_file_path}")

        create_object_csv(entry, folder_path)

if __name__ == '__main__':
    main()