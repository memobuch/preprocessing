import pandas as pd
import json
import os

#1. Create a dictionary

df = pd.read_csv('memobuch_demodata.csv', sep=';')
demo_dict = df.to_dict(orient='records')

print(demo_dict[0])

#2. Create a folder structure
output_root = 'demodata'

for entry in demo_dict:
    folder_name = str(entry['Identifikatornummer'])
    folder_path = os.path.join(output_root, folder_name)
    os.makedirs(folder_path, exist_ok=True)

#3. Save entries as json files

for entry in demo_dict:
    folder_name = str(entry['Identifikatornummer'])
    folder_path = os.path.join(output_root, folder_name)
    filename = f"{str(entry['Identifikatornummer'])}.json"
   
    json_file_path = os.path.join(folder_path, filename)
    with open(json_file_path, 'w') as json_file:
        json.dump(entry, json_file)