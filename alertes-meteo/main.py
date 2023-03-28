import urllib.request
import datetime
import zipfile
import os
import re
import shutil
import json
import xml.etree.ElementTree as Et

data = []


def download_files(start_year, end_year):
    base_url = "http://vigilance-public.meteo.fr/telechargement.php?dateVigi={date}&base=vigilance{vigilance}"
    start_date = datetime.date(start_year, 1, 1)
    end_date = datetime.date(end_year, 12, 31)
    delta = datetime.timedelta(days=1)

    zip_filename = f"{start_year}_{end_year}_CMIRIC.zip"
    with zipfile.ZipFile(zip_filename, "w") as zip_file:
        while start_date <= end_date:
            date_str = start_date.strftime("%Y-%m-%d")
            dirname = start_date.strftime("%Y_%m_%d")
            url = base_url.format(date=date_str, vigilance="1a3" if start_year in [2010, 2011] else "4")
            filename = f"{dirname}.zip"

            print(f"Downloading {filename} from {url}")
            try:
                urllib.request.urlretrieve(url, filename)
                with zipfile.ZipFile(filename, "r") as zip_ref:
                    files_to_extract = [
                        zip_info for zip_info in zip_ref.infolist()
                        if re.match(rf"{dirname}.*CMIRIC\.xml", zip_info.filename)
                    ]
                    if files_to_extract:
                        # Crée un répertoire pour stocker les fichiers extraits
                        os.makedirs(dirname, exist_ok=True)
                        for zip_info in files_to_extract:
                            zip_ref.extract(zip_info.filename, dirname)
                            print(f"Extracted {zip_info.filename} to {dirname}")

                        # Add json info
                        add_json_info(f"./{dirname}/{zip_info.filename}", dirname)

                        # Ajoute les fichiers extraits au fichier zip global
                        for file_to_extract in files_to_extract:
                            file_path = os.path.join(dirname, file_to_extract.filename)
                            zip_file.write(file_path, file_to_extract.filename)
            except urllib.error.HTTPError:
                print(f"Error: could not download file {filename} from {url}")
            os.remove(filename)
            start_date += delta
            if os.path.exists(dirname):
                shutil.rmtree(dirname)
    print("All files downloaded and extracted")
    create_global_json()


def add_json_info(filepath, file_date):
    data_to_add = {}
    # charger le fichier XML
    tree = Et.parse(filepath)
    root = tree.getroot()

    # extraire les informations nécessaires
    phenomene = root.find("Phenomenes")

    type_event = phenomene.attrib["evenement"]

    if type_event is not None:
        data_to_add["type"] = type_event

    date = phenomene.find("Datevigilance")

    if date is not None:
        is_happening = date.text == 'Phénomène en cours.'

        if not is_happening:
            return

        data_to_add["date"] = file_date

    [localisation_tag, _, etat_tag] = root.findall("Descriptif")

    try:
        localisation = localisation_tag.find("Titre").find("Paragraphe").find("Texte").text
        data_to_add["localisation"] = localisation
    except Exception as e:
        print(e)

    try:
        etat = etat_tag.find("Titre").find("Paragraphe").find("Intitule").text
        if "Orange" not in etat and "Rouge" not in etat:
            return

        data_to_add["etat"] = "Orange" if "Orange" in etat else "Rouge"
    except Exception as e:
        print(e)

    data.append(data_to_add)


def create_global_json():
    grouped_data = {}
    for item in data:
        date = item['date']
        if date not in grouped_data:
            grouped_data[date] = []
        grouped_data[date].append(item)

    # écrire les données dans un fichier JSON
    with open('global_data.json', 'w') as f:
        json.dump(grouped_data, f)


download_files(2012, 2014)
