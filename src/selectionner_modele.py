# Sélection du modèle sur l'année de validation 2022.
#
# Les candidats sont construits sur 2019-2021, puis comparés sur 2022 :
#   - le modèle en V : un seul seuil T0 pour le chauffage et la climatisation ;
#   - le modèle à plateau : un seuil de chauffage et un seuil de climatisation
#     plus élevé, avec une demande constante entre les deux.
# Chaque candidat est testé sans et avec une tendance (croissance annuelle).
# Le jour de la semaine est codé en 3 groupes : lundi-jeudi, vendredi, fin de semaine.
# L'année 2023, réservée au test final, n'est jamais utilisée ici.

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

RACINE = Path(__file__).resolve().parent.parent
FICHIER_DONNEES = RACINE / "data" / "processed" / "donnees_journalieres.csv"
FICHIER_FIGURE = RACINE / "figures" / "selection_seuil.png"
SEUILS = np.arange(5, 24.5, 0.5)  # seuils testés : 5, 5,5, ..., 24 °C
DEBUT = pd.Timestamp("2019-01-01")  # origine de la tendance

GROUPES = {"lundi": "lun-jeu", "mardi": "lun-jeu", "mercredi": "lun-jeu", "jeudi": "lun-jeu",
           "vendredi": "vendredi", "samedi": "fin de semaine", "dimanche": "fin de semaine"}
ORDRE_GROUPES = ["lun-jeu", "vendredi", "fin de semaine"]


def variables(donnees: pd.DataFrame, seuil_chauffage: float, seuil_climatisation: float,
              tendance: bool) -> pd.DataFrame:
    """Construit les variables explicatives : degrés-jours, tendance et jour de la semaine."""
    t = donnees["temp_moyenne"]
    X = pd.DataFrame({
        "chauffage": (seuil_chauffage - t).clip(lower=0),          # degrés sous le seuil
        "climatisation": (t - seuil_climatisation).clip(lower=0),  # degrés au-dessus du seuil
    })
    if tendance:
        X["tendance"] = (donnees["date"] - DEBUT).dt.days / 365.25  # années depuis 2019
    groupes = pd.Categorical(donnees["jour_semaine"].map(GROUPES), categories=ORDRE_GROUPES)
    # Une indicatrice par groupe, sauf lundi-jeudi, qui sert de référence.
    indicatrices = pd.get_dummies(groupes, drop_first=True, dtype=float)
    indicatrices.index = donnees.index
    return sm.add_constant(pd.concat([X, indicatrices], axis=1))


def erreurs_validation(apprentissage: pd.DataFrame, validation: pd.DataFrame,
                       seuil_chauffage: float, seuil_climatisation: float,
                       tendance: bool) -> tuple[float, float]:
    """Ajuste le modèle sur l'apprentissage et renvoie son erreur moyenne et son biais sur la validation."""
    X_apprentissage = variables(apprentissage, seuil_chauffage, seuil_climatisation, tendance)
    modele = sm.OLS(apprentissage["demande_mw"], X_apprentissage).fit()
    prevision = modele.predict(variables(validation, seuil_chauffage, seuil_climatisation, tendance))
    ecart = validation["demande_mw"] - prevision
    return ecart.abs().mean(), ecart.mean()  # biais > 0 : le modèle sous-estime


def figure_seuil(resultats: pd.DataFrame) -> None:
    """L'erreur de validation du modèle en V selon son seuil T0, sans et avec tendance."""
    fig, ax = plt.subplots(figsize=(7, 4))
    for tendance, nom in [(False, "Sans tendance"), (True, "Avec tendance")]:
        courbe = resultats[(resultats["modele"] == "V") & (resultats["tendance"] == tendance)]
        ax.plot(courbe["seuil_chauffage"], courbe["mae"], marker="o", markersize=3, label=nom)
    ax.set_title("Modèle en V : erreur sur l'année de validation selon le seuil T0")
    ax.set_xlabel("Seuil T0 (°C)")
    ax.set_ylabel("Erreur absolue moyenne (MW)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FICHIER_FIGURE, dpi=150)
    plt.close(fig)
    print(f"\nFigure enregistrée : {FICHIER_FIGURE}")


def main() -> None:
    donnees = pd.read_csv(FICHIER_DONNEES, parse_dates=["date"])
    annee = donnees["date"].dt.year
    apprentissage = donnees[annee <= 2021]
    validation = donnees[annee == 2022]
    print(f"Apprentissage : {len(apprentissage)} jours (2019-2021)")
    print(f"Validation    : {len(validation)} jours (2022)")

    resultats = []
    for tendance in [False, True]:
        for seuil_chauffage in SEUILS:
            for seuil_climatisation in SEUILS[SEUILS >= seuil_chauffage]:
                mae, biais = erreurs_validation(apprentissage, validation,
                                                seuil_chauffage, seuil_climatisation, tendance)
                resultats.append({
                    "modele": "V" if seuil_chauffage == seuil_climatisation else "plateau",
                    "tendance": tendance,
                    "seuil_chauffage": seuil_chauffage,
                    "seuil_climatisation": seuil_climatisation,
                    "mae": mae,
                    "biais": biais,
                })
    resultats = pd.DataFrame(resultats)

    # Pour chaque combinaison (modèle, tendance), on garde les seuils qui minimisent l'erreur.
    meilleurs = resultats.loc[resultats.groupby(["modele", "tendance"])["mae"].idxmin()]
    print(f"\n{len(resultats)} versions testées. Meilleure version de chaque candidat :")
    print(meilleurs.sort_values("mae").round(1).to_string(index=False))

    figure_seuil(resultats)


if __name__ == "__main__":
    main()