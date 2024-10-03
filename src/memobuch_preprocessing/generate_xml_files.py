import pandas as pd
import json
import os
from bs4 import BeautifulSoup as bs



def main():
    #1. Create a dictionary

    df = pd.read_csv('memobuch_demodata.csv', sep=';')
    demo_dict = df.to_dict(orient='records')

    #2. Open xml template
    with open('xml_template', 'r') as f:
        xml_template = f.read()

    soup = bs(xml_template, 'xml')

    output_root = 'demodata'

    #3. insert values in the title element
    for entry in demo_dict:
        title = entry['Nachname'] + " " + entry['Vorname']
        title_element = xml_template.find('dc:title')
        title_element.string = title

    #3. Save entries as xml files
        folder_name = str(entry['Identifikatornummer'])
        folder_path = os.path.join(output_root, folder_name)
        filename = "DC.xml"

        xml_file_path = os.path.join(folder_path, filename)
        with open(xml_file_path, 'w', encoding='utf-8') as xml_file:
            xml_file.write(str(soup.pretify()))


# if __name__ == '__main__':
#     main()