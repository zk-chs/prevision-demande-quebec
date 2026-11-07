# Source : Environnement et Changement climatique Canada, données climatiques historiques 
# https://climate.weather.gc.ca/
# Données quotidiennes de 2019 à 2023 pour cinq stations candidates.

from pathlib import Path
import pandas as pd
import requests

ANNEES = range(2019, 2024)
STATIONS = {  # Station ID : ville
    53001: "Gatineau",
    49568: "Ottawa",
    51157: "Montréal",
    30165: "Montréal",
    51457: "Québec",
    26892: "Québec",
}
URL = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
DOSSIER = Path(__file__).resolve().parent.parent / "data" / "raw" / "meteo"


def telecharger(station: int, annee: int) -> Path:
    """Télécharge les données quotidiennes d'une station pour une année."""
    chemin = DOSSIER / f"station_{station}_{annee}.csv"
    if chemin.exists():
        return chemin

    parametres = {
        "format": "csv",
        "stationID": station,
        "Year": annee,
        "Month": 1,
        "Day": 1,
        "timeframe": 2,  
        "submit": "Download Data",
    }
    reponse = requests.get(URL, params=parametres, timeout=30)
    reponse.raise_for_status()
    chemin.write_bytes(reponse.content)
    return chemin


def bilan(station: int, ville: str) -> None:
    """Affiche le nom de la station, le nombre de jours et les températures manquantes."""
    fichiers = [DOSSIER / f"station_{station}_{annee}.csv" for annee in ANNEES]
    df = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in fichiers], ignore_index=True)
    manquants = df["Mean Temp (°C)"].isna().sum()
    print(f"{ville:<9} {station:>6}  {df['Station Name'].iloc[0]:<38} "
          f"{len(df):>5} jours  {manquants:>4} manquants")


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)
    for station in STATIONS:
        for annee in ANNEES:
            telecharger(station, annee)
        print(f"Station {station} : 5 années téléchargées")

    print("\n=== Températures moyennes quotidiennes, 2019 à 2023 ===")
    for station, ville in STATIONS.items():
        bilan(station, ville)


if __name__ == "__main__":
    main()