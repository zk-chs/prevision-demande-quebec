# Exploration des données : des graphiques pour comprendre la relation entre la demande d'électricité, la température et le jour de la semaine.
# Les figures sont enregistrées dans le dossier figures/.

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
FICHIER_DONNEES = RACINE / "data" / "processed" / "donnees_journalieres.csv"
DOSSIER_FIGURES = RACINE / "figures"
VILLES = {"temp_gatineau": "Gatineau", "temp_montreal": "Montréal", "temp_quebec": "Québec"}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def enregistrer(fig: plt.Figure, nom: str) -> None:
    #Enregistre une figure en image dans le dossier figures/.

    DOSSIER_FIGURES.mkdir(exist_ok=True)
    chemin = DOSSIER_FIGURES / nom
    fig.tight_layout()
    fig.savefig(chemin, dpi=150)
    plt.close(fig)
    print(f"Figure enregistrée : {chemin}")


def figure_demande_temps(donnees: pd.DataFrame) -> None:
    #La demande moyenne journalière de 2019 à 2023.

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(donnees["date"], donnees["demande_mw"], linewidth=0.8)
    ax.axvspan(pd.Timestamp("2023-01-01"), pd.Timestamp("2023-12-31"),
               color="grey", alpha=0.15, label="Période de test (2023)")
    ax.set_title("Demande moyenne journalière d'électricité au Québec, 2019 à 2023")
    ax.set_xlabel("Date")
    ax.set_ylabel("Demande (MW)")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    enregistrer(fig, "demande_temps.png")

    jour_max = donnees.loc[donnees["demande_mw"].idxmax()]
    jour_min = donnees.loc[donnees["demande_mw"].idxmin()]
    print(f"  Demande la plus forte : {jour_max['demande_mw']:.0f} MW le {jour_max['date']:%Y-%m-%d}")
    print(f"  Demande la plus faible : {jour_min['demande_mw']:.0f} MW le {jour_min['date']:%Y-%m-%d}")

def figure_demande_temperature(donnees: pd.DataFrame) -> None:
    #La demande selon la température, un graphique par ville.

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ax, (colonne, ville) in zip(axes, VILLES.items()):
        ax.scatter(donnees[colonne], donnees["demande_mw"], s=6, alpha=0.4)
        ax.set_title(ville)
        ax.set_xlabel("Température moyenne du jour (°C)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("Demande (MW)")
    fig.suptitle("Demande moyenne journalière selon la température, 2019 à 2023")
    enregistrer(fig, "demande_temperature.png")

    print("  Corrélation entre les températures des trois villes :")
    print(donnees[list(VILLES)].corr().round(3).to_string())

def figure_jour_semaine(donnees: pd.DataFrame) -> None:
    #La demande selon la température moyenne, en semaine et en fin de semaine.
    fin_semaine = donnees["jour_semaine"].isin(["samedi", "dimanche"])
    semaine = donnees[~fin_semaine]
    weekend = donnees[fin_semaine]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(semaine["temp_moyenne"], semaine["demande_mw"], s=6, alpha=0.4,
               label="Lundi à vendredi")
    ax.scatter(weekend["temp_moyenne"], weekend["demande_mw"], s=6, alpha=0.6,
               label="Samedi et dimanche")
    ax.set_title("Demande selon la température moyenne des trois villes")
    ax.set_xlabel("Température moyenne du jour (°C)")
    ax.set_ylabel("Demande (MW)")
    ax.legend()
    ax.grid(alpha=0.3)
    enregistrer(fig, "demande_jour_semaine.png")

    moyennes = donnees.groupby("jour_semaine")["demande_mw"].mean().reindex(JOURS)
    print("  Demande moyenne par jour de la semaine (MW) :")
    print(moyennes.round(0).to_string())

def main() -> None:
    donnees = pd.read_csv(FICHIER_DONNEES, parse_dates=["date"])
    figure_demande_temps(donnees)
    figure_demande_temperature(donnees)
    figure_jour_semaine(donnees)


if __name__ == "__main__":
    main()