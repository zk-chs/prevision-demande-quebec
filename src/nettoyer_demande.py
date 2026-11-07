# Nettoyage de la demande horaire d'Hydro-Québec et calcul de la demande moyenne journalière.

# Règle de traitement des valeurs manquantes :
#   un jour qui contient au moins une heure manquante est retiré. Ainsi, chaque moyenne conservée repose sur une journée complète.

from pathlib import Path
import pandas as pd

ANNEES = range(2019, 2024)

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_BRUT = RACINE / "data" / "raw" / "hydroquebec"
FICHIER_SORTIE = RACINE / "data" / "processed" / "demande_journaliere.csv"


def lire_annee(annee: int) -> pd.DataFrame:
    #Lit le fichier d'une année et corrige la date de sa dernière ligne si besoin

    tableau = pd.read_excel(DOSSIER_BRUT / f"demande_{annee}.xlsx")
    fin_attendue = pd.Timestamp(annee + 1, 1, 1)
    if tableau["Date"].iloc[-1] != fin_attendue:
        print(f"Correction {annee} : {tableau['Date'].iloc[-1]} remplacée par {fin_attendue}")
        tableau.loc[tableau.index[-1], "Date"] = fin_attendue
    return tableau


def charger() -> pd.DataFrame:
    #Lit les fichiers annuels et les empile en un seul tableau horaire
    tableaux = [lire_annee(annee) for annee in ANNEES]
    horaire = pd.concat(tableaux, ignore_index=True)
    return horaire.rename(columns={"Date": "date_heure", "Moyenne (MW)": "demande_mw"})

def moyennes_journalieres(horaire: pd.DataFrame) -> pd.DataFrame:
    #Calcule la demande moyenne de chaque jour et indique si le jour est complet
    
    jour = (horaire["date_heure"] - pd.Timedelta(hours=1)).dt.date
    journalier = horaire.groupby(jour).agg(
        demande_mw=("demande_mw", "mean"),
        heures=("demande_mw", "size"),          # nombre de lignes du jour (23, 24 ou 25)
        heures_valides=("demande_mw", "count"),  # nombre de valeurs non manquantes
    )
    journalier.index.name = "date"
    journalier["complet"] = journalier["heures_valides"] == journalier["heures"]
    return journalier


def main() -> None:
    horaire = charger()
    journalier = moyennes_journalieres(horaire)
    complets = journalier[journalier["complet"]]
    retires = journalier[~journalier["complet"]]

    FICHIER_SORTIE.parent.mkdir(parents=True, exist_ok=True)
    complets[["demande_mw"]].round(2).to_csv(FICHIER_SORTIE)

    print("=== Bilan du nettoyage ===")
    print(f"Heures lues              : {len(horaire)}")
    print(f"Heures manquantes        : {horaire['demande_mw'].isna().sum()}")
    print(f"\nJours au total           : {len(journalier)}")
    print(f"Jours complets conservés : {len(complets)}")
    print(f"Jours retirés            : {len(retires)}")
    print(retires[["heures", "heures_valides"]])
    print("\nNombre d'heures par jour (24, sauf changements d'heure) :")
    print(journalier["heures"].value_counts())
    print(f"\nFichier écrit : {FICHIER_SORTIE}")


if __name__ == "__main__":
    main()