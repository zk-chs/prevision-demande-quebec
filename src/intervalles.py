# Intervalles d'incertitude des prévisions, à 90 %.
#
# Méthode : la largeur des intervalles vient des erreurs commises sur des jours
# que le modèle ne connaissait pas (erreurs « hors échantillon »).
# Pour une année de validation donnée, le modèle est ajusté sur les années précédentes,
# puis prévoit cette année. Les quantiles à 5 % et 95 % de ses erreurs donnent les bornes,
# séparément pour les jours froids (sous T0) et les jours doux.
#
# Deux versions sont comparées sur 2023 :
#   - « 1 an » : erreurs de 2022 seulement (le test officiel, défini avant de voir 2023) ;
#   - « 2 ans » : erreurs de 2021 et de 2022 (analyse complémentaire, ajoutée après
#     le test pour mieux capter les variations d'une année à l'autre).
# Les bornes « 1 an » sont enregistrées pour l'application.

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from modele import T0, ajuster, prevoir

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "data" / "processed"
DOSSIER_FIGURES = RACINE / "figures"
NIVEAU = 0.90
BAS, HAUT = (1 - NIVEAU) / 2, 1 - (1 - NIVEAU) / 2  # quantiles 5 % et 95 %
VERSIONS = {"1 an (2022)": [2022], "2 ans (2021-2022)": [2021, 2022]}


def saison(donnees: pd.DataFrame) -> pd.Series:
    """« froid » sous le seuil T0, « doux » au-dessus."""
    froid = donnees["temp_moyenne"] < T0
    return froid.map({True: "froid", False: "doux"}).rename("saison")


def erreurs_hors_echantillon(donnees: pd.DataFrame, annee_validation: int) -> pd.DataFrame:
    """Erreurs d'un modèle ajusté sur les années précédant l'année de validation."""
    annee = donnees["date"].dt.year
    apprentissage = donnees[annee < annee_validation]
    validation = donnees[annee == annee_validation]
    modele = ajuster(apprentissage)
    erreur = validation["demande_mw"] - prevoir(modele, validation)
    return pd.DataFrame({"erreur": erreur, "saison": saison(validation)})


def calculer_bornes(donnees: pd.DataFrame, annees_validation: list[int]) -> pd.DataFrame:
    """Les quantiles des erreurs hors échantillon, regroupées sur les années de validation."""
    erreurs = pd.concat([erreurs_hors_echantillon(donnees, a) for a in annees_validation])
    bornes = erreurs.groupby("saison")["erreur"].quantile([BAS, HAUT]).unstack()
    bornes.columns = ["borne_basse", "borne_haute"]
    return bornes


def appliquer(p: pd.DataFrame, bornes: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les bornes de l'intervalle aux prévisions de 2023."""
    s = saison(p)
    p = p.copy()
    p["borne_basse"] = p["modele_v"] + s.map(bornes["borne_basse"])
    p["borne_haute"] = p["modele_v"] + s.map(bornes["borne_haute"])
    return p


def couverture(p: pd.DataFrame) -> pd.DataFrame:
    """La part des jours de 2023 dont la demande réelle tombe dans l'intervalle."""
    s = saison(p)
    dedans = p["reel"].between(p["borne_basse"], p["borne_haute"])
    resume = pd.DataFrame({
        "jours": s.value_counts(),
        "couverture (%)": dedans.groupby(s).mean() * 100,
        "sous la borne basse (%)": (p["reel"] < p["borne_basse"]).groupby(s).mean() * 100,
        "au-dessus de la borne haute (%)": (p["reel"] > p["borne_haute"]).groupby(s).mean() * 100,
        "largeur moyenne (MW)": (p["borne_haute"] - p["borne_basse"]).groupby(s).mean(),
    })
    resume.loc["ensemble"] = [len(p), dedans.mean() * 100,
                              (p["reel"] < p["borne_basse"]).mean() * 100,
                              (p["reel"] > p["borne_haute"]).mean() * 100,
                              (p["borne_haute"] - p["borne_basse"]).mean()]
    resume["jours"] = resume["jours"].astype(int)
    return resume


def figure_intervalles(p: pd.DataFrame, version: str, nom_fichier: str) -> None:
    """La demande réelle de 2023 et l'intervalle de prévision à 90 %."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(p["date"], p["borne_basse"], p["borne_haute"],
                    alpha=0.3, label="Intervalle de prévision à 90 %")
    ax.plot(p["date"], p["reel"], linewidth=0.8, color="black", label="Demande réelle")
    ax.set_title(f"Demande réelle et intervalle à 90 % (erreurs de validation : {version}), 2023")
    ax.set_xlabel("Date")
    ax.set_ylabel("Demande (MW)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(DOSSIER_FIGURES / nom_fichier, dpi=150)
    plt.close(fig)
    print(f"Figure enregistrée : {DOSSIER_FIGURES / nom_fichier}")


def main() -> None:
    donnees = pd.read_csv(DOSSIER / "donnees_journalieres.csv", parse_dates=["date"])
    previsions = pd.read_csv(DOSSIER / "previsions_2023.csv", parse_dates=["date"])
    fichiers = {"1 an (2022)": "intervalles_2023.png", "2 ans (2021-2022)": "intervalles_2023_deux_ans.png"}

    for version, annees in VERSIONS.items():
        bornes = calculer_bornes(donnees, annees)
        p = appliquer(previsions, bornes)
        print(f"\n=== Version {version} ===")
        print("Bornes autour de la prévision (MW) :")
        print(bornes.round(0).to_string())
        print(f"Couverture sur 2023 (objectif : {NIVEAU:.0%}) :")
        print(couverture(p).round(1).to_string())
        figure_intervalles(p, version, fichiers[version])

    # L'application utilise la version « 1 an » : les erreurs de 2022 viennent d'un modèle
    # ajusté sur trois ans, plus proche du modèle final que celui de 2021 (deux ans).
    calculer_bornes(donnees, VERSIONS["1 an (2022)"]).to_csv(DOSSIER / "bornes_intervalle.csv")
    # L'application utilise la version « 2 ans ».
    #calculer_bornes(donnees, VERSIONS["2 ans (2021-2022)"]).to_csv(DOSSIER / "bornes_intervalle.csv")
    print(f"\nBornes de l'application enregistrées : {DOSSIER / 'bornes_intervalle.csv'}")


if __name__ == "__main__":
    main()