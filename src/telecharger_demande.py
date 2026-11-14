# Source : Hydro-Québec, données ouvertes (CC-BY-NC 4.0)
# https://www.hydroquebec.com/documents-data/open-data/history-electricity-demand-quebec/


from pathlib import Path
import pandas as pd
import requests

ANNEES = range(2019, 2024)  
URL = (
    "https://www.hydroquebec.com/data/documents-donnees/donnees-ouvertes/"
    "xlsx/historique-demande/{annee}-demande-electricite-quebec.xlsx"
)
DOSSIER = Path(__file__).resolve().parent.parent / "data" / "raw" / "hydroquebec"


def telecharger(annee: int) -> Path:
    chemin = DOSSIER / f"demande_{annee}.xlsx"

    if chemin.exists():
        print(f"{annee} : déjà téléchargé")
        return chemin

    reponse = requests.get(URL.format(annee=annee), timeout=30)
    reponse.raise_for_status() 
    chemin.write_bytes(reponse.content)
    print(f"{annee} : téléchargé ({len(reponse.content) / 1024:.0f} ko)")
    return chemin


def apercu(chemin: Path) -> None:
    df = pd.read_excel(chemin)
    print(f"\n--- {chemin.name} : {len(df)} lignes ---")
    print(df.head(3))
    print()


def main() -> None:
    DOSSIER.mkdir(parents=True, exist_ok=True)

    for annee in ANNEES:
        chemin = telecharger(annee)
        apercu(chemin)


if __name__ == "__main__":
    main()
