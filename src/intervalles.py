# Intervalles d'incertitude des prévisions, à 90 %.
#
# Méthode : la largeur des intervalles vient des erreurs commises sur des jours
# que le modèle ne connaissait pas.
#   1. Le modèle est ajusté sur 2019-2021, puis prévoit l'année de validation 2022.
#   2. Les erreurs de 2022 donnent les bornes à 5 % et à 95 %, séparément pour
#      les jours froids (sous T0) et les jours doux, car les erreurs sont plus grandes l'hiver.
#   3. Ces bornes sont ajoutées aux prévisions de 2023 du modèle final, et l'on compte
#      la part des jours dont la demande réelle tombe dans l'intervalle.

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from modele import T0, ajuster, prevoir

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "data" / "processed"
FICHIER_FIGURE = RACINE / "figures" / "intervalles_2023.png"
NIVEAU = 0.90
BAS, HAUT = (1 - NIVEAU) / 2, 1 - (1 - NIVEAU) / 2  # quantiles 5 % et 95 %


def saison(donnees: pd.DataFrame) -> pd.Series:
    """« froid » sous le seuil T0, « doux » au-dessus."""
    froid = donnees["temp_moyenne"] < T0
    return froid.map({True: "froid", False: "doux"}).rename("saison")


def bornes_validation(donnees: pd.DataFrame) -> pd.DataFrame:
    """Les quantiles des erreurs de 2022, pour un modèle ajusté sur 2019-2021."""
    annee = donnees["date"].dt.year
    apprentissage, validation = donnees[annee <= 2021], donnees[annee == 2022]
    modele = ajuster(apprentissage)
    erreur = validation["demande_mw"] - prevoir(modele, validation)
    bornes = erreur.groupby(saison(validation)).quantile([BAS, HAUT]).unstack()
    bornes.columns = ["borne_basse", "borne_haute"]
    return bornes


def figure_intervalles(p: pd.DataFrame) -> None:
    """La demande réelle de 2023 et l'intervalle de prévision à 90 %."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(p["date"], p["borne_basse"], p["borne_haute"],
                    alpha=0.3, label="Intervalle de prévision à 90 %")
    ax.plot(p["date"], p["reel"], linewidth=0.8, color="black", label="Demande réelle")
    ax.set_title("Demande réelle et intervalle de prévision à 90 %, année de test 2023")
    ax.set_xlabel("Date")
    ax.set_ylabel("Demande (MW)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FICHIER_FIGURE, dpi=150)
    plt.close(fig)
    print(f"\nFigure enregistrée : {FICHIER_FIGURE}")


def main() -> None:
    donnees = pd.read_csv(DOSSIER / "donnees_journalieres.csv", parse_dates=["date"])

    # 1-2. Les bornes, à partir des erreurs de l'année de validation
    bornes = bornes_validation(donnees)
    bornes.to_csv(DOSSIER / "bornes_intervalle.csv")
    print("=== Bornes de l'intervalle à 90 %, tirées des erreurs de 2022 (MW) ===")
    print(bornes.round(0).to_string())

    # 3. Application aux prévisions de 2023
    p = pd.read_csv(DOSSIER / "previsions_2023.csv", parse_dates=["date"])
    s = saison(p)
    p["borne_basse"] = p["modele_v"] + s.map(bornes["borne_basse"])
    p["borne_haute"] = p["modele_v"] + s.map(bornes["borne_haute"])

    dedans = p["reel"].between(p["borne_basse"], p["borne_haute"])
    resume = pd.DataFrame({
        "jours": s.value_counts(),
        "couverture (%)": dedans.groupby(s).mean() * 100,
        "sous la borne basse (%)": (p["reel"] < p["borne_basse"]).groupby(s).mean() * 100,
        "au-dessus de la borne haute (%)": (p["reel"] > p["borne_haute"]).groupby(s).mean() * 100,
        "largeur moyenne (MW)": (p["borne_haute"] - p["borne_basse"]).groupby(s).mean(),
    })
    print(f"\n=== Couverture sur 2023 (objectif : {NIVEAU:.0%}) ===")
    print(resume.round(1).to_string())
    print(f"\nCouverture sur l'ensemble de 2023 : {dedans.mean():.1%}")

    figure_intervalles(p)


if __name__ == "__main__":
    main()