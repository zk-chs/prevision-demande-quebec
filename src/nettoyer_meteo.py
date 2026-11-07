# Nettoyage des températures quotidiennes d'Environnement Canada.

from pathlib import Path
import pandas as pd

ANNEES = range(2019, 2024)
STATIONS = {  # ville : (station principale, station de secours)
    "gatineau": (53001, 49568),
    "montreal": (30165, 51157),
    "quebec": (26892, 51457),
}

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_BRUT = RACINE / "data" / "raw" / "meteo"
FICHIER_SORTIE = RACINE / "data" / "processed" / "temperature_journaliere.csv"


def lire_station(station: int) -> pd.Series:
    """Renvoie la température moyenne quotidienne d'une station, indexée par date."""
    fichiers = [DOSSIER_BRUT / f"station_{station}_{annee}.csv" for annee in ANNEES]
    df = pd.concat([pd.read_csv(f, encoding="utf-8-sig") for f in fichiers])
    df["date"] = pd.to_datetime(df["Date/Time"]).dt.date
    return df.set_index("date")["Mean Temp (°C)"]


def comparer(principale: pd.Series, secours: pd.Series) -> None:
    """Vérifie que les deux stations mesurent la même température."""
    communs = principale.notna() & secours.notna()
    ecart = (principale[communs] - secours[communs]).abs()
    correlation = principale[communs].corr(secours[communs])
    print(f"  Jours mesurés par les deux stations : {communs.sum()}")
    print(f"  Écart moyen : {ecart.mean():.2f} °C   écart maximal : {ecart.max():.1f} °C")
    print(f"  Corrélation : {correlation:.3f}")


def temperature_ville(ville: str, principale_id: int, secours_id: int) -> pd.Series:
    """Température de la station principale, complétée par la station de secours."""
    print(f"\n{ville.capitalize()} : station {principale_id}, secours {secours_id}")
    principale = lire_station(principale_id)
    secours = lire_station(secours_id)
    comparer(principale, secours)

    manquants = principale.isna().sum()
    completee = principale.fillna(secours)
    print(f"  Jours manquants : {manquants}, dont {manquants - completee.isna().sum()} "
          f"comblés par la station {secours_id}")
    return completee


def main() -> None:
    print("=== Nettoyage des températures ===")
    temperatures = pd.DataFrame({
        f"temp_{ville}": temperature_ville(ville, principale, secours)
        for ville, (principale, secours) in STATIONS.items()
    })
    temperatures.index.name = "date"

    incomplets = temperatures.isna().any(axis=1)
    complets = temperatures[~incomplets]

    FICHIER_SORTIE.parent.mkdir(parents=True, exist_ok=True)
    complets.to_csv(FICHIER_SORTIE)

    print("\n=== Bilan ===")
    print(f"Jours au total           : {len(temperatures)}")
    print(f"Jours retirés            : {incomplets.sum()}")
    print(f"Jours complets conservés : {len(complets)}")
    print("Jours encore manquants par ville :")
    print(temperatures.isna().sum().to_string())
    print(f"\nFichier écrit : {FICHIER_SORTIE}")


if __name__ == "__main__":
    main()