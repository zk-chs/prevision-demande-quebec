# Construction du jeu de données final : une ligne par jour, avec la demande
# moyenne journalière, les températures des trois villes et le jour de la semaine.

from pathlib import Path
import pandas as pd

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

DOSSIER = Path(__file__).resolve().parent.parent / "data" / "processed"
FICHIER_SORTIE = DOSSIER / "donnees_journalieres.csv"


def main() -> None:
    demande = pd.read_csv(DOSSIER / "demande_journaliere.csv", parse_dates=["date"])
    temperatures = pd.read_csv(DOSSIER / "temperature_journaliere.csv", parse_dates=["date"])

    # Fusion sur la date : on garde les jours présents dans les deux fichiers.
    donnees = demande.merge(temperatures, on="date", how="inner")
    donnees["jour_semaine"] = [JOURS[i] for i in donnees["date"].dt.day_of_week]

    donnees.to_csv(FICHIER_SORTIE, index=False)

    annee = donnees["date"].dt.year
    print("=== Jeu de données final ===")
    print(f"Jours de demande      : {len(demande)}")
    print(f"Jours de température  : {len(temperatures)}")
    print(f"Jours après fusion    : {len(donnees)}")
    print(f"  dont 2019-2022 (construction du modèle) : {(annee <= 2022).sum()}")
    print(f"  dont 2023 (test)                        : {(annee == 2023).sum()}")
    print("\nPremières lignes :")
    print(donnees.head(7).to_string(index=False))
    print("\nRésumé statistique :")
    print(donnees.describe().round(1).to_string())
    print(f"\nFichier écrit : {FICHIER_SORTIE}")


if __name__ == "__main__":
    main()