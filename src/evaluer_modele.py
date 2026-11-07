# Évaluation finale du modèle.
#
# Le modèle retenu est ajusté sur 2019-2022, puis testé une seule fois sur 2023,
# face à deux points de comparaison :
#   - la climatologie : la demande moyenne de 2019-2022 pour le même mois
#     et le même type de jour (semaine ou fin de semaine) ;
#   - la droite unique : la même régression, mais avec la température brute
#     au lieu des deux degrés-jours.

from pathlib import Path
import pandas as pd
import statsmodels.api as sm

from modele import ajuster, prevoir, variables

DOSSIER = Path(__file__).resolve().parent.parent / "data" / "processed"
PART_FROIDE = 0.10  # les 10 % de jours les plus froids de 2023


def fin_de_semaine(donnees: pd.DataFrame) -> pd.Series:
    return donnees["jour_semaine"].isin(["samedi", "dimanche"])


def climatologie(apprentissage: pd.DataFrame, test: pd.DataFrame) -> pd.Series:
    """Prévision sans outil : la demande moyenne du même mois et du même type de jour."""
    moyennes = apprentissage.groupby(
        [apprentissage["date"].dt.month, fin_de_semaine(apprentissage)])["demande_mw"].mean()
    cles = list(zip(test["date"].dt.month, fin_de_semaine(test)))
    return pd.Series(moyennes.loc[cles].values, index=test.index)


def variables_droite(donnees: pd.DataFrame) -> pd.DataFrame:
    """Variables de la droite unique : la température brute remplace les degrés-jours."""
    X = variables(donnees).drop(columns=["chauffage", "climatisation"])
    X.insert(1, "temperature", donnees["temp_moyenne"])
    return X


def mesures(reel: pd.Series, prevu: pd.Series, froid: pd.Series) -> dict:
    """Les mesures d'erreur communes à tous les modèles."""
    ecart = reel - prevu
    return {
        "MAE (MW)": ecart.abs().mean(),
        "MAPE (%)": (ecart.abs() / reel).mean() * 100,
        "Biais (MW)": ecart.mean(),                     # > 0 : sous-estimation
        "MAE jours froids (MW)": ecart[froid].abs().mean(),
    }


def main() -> None:
    donnees = pd.read_csv(DOSSIER / "donnees_journalieres.csv", parse_dates=["date"])
    apprentissage = donnees[donnees["date"].dt.year <= 2022]
    test = donnees[donnees["date"].dt.year == 2023]

    # 1. Le modèle retenu, ajusté sur 2019-2022
    modele = ajuster(apprentissage)
    ic = modele.conf_int()
    resume = pd.DataFrame({
        "coefficient": modele.params,
        "IC 95 % bas": ic[0],
        "IC 95 % haut": ic[1],
        "p-valeur": modele.pvalues,
    })
    print(f"=== Modèle en V ajusté sur 2019-2022 ({len(apprentissage)} jours) ===")
    print(resume.round(3).to_string())

    # 2. La droite unique, ajustée sur les mêmes jours
    droite = sm.OLS(apprentissage["demande_mw"], variables_droite(apprentissage)).fit()
    print(f"\nR² sur 2019-2022 : modèle en V {modele.rsquared:.3f}, droite unique {droite.rsquared:.3f}")

    # 3. Le test sur 2023
    seuil_froid = test["temp_moyenne"].quantile(PART_FROIDE)
    froid = test["temp_moyenne"] <= seuil_froid
    previsions = pd.DataFrame({
        "date": test["date"],
        "temp_moyenne": test["temp_moyenne"],
        "reel": test["demande_mw"],
        "modele_v": prevoir(modele, test),
        "droite": droite.predict(variables_droite(test)),
        "climatologie": climatologie(apprentissage, test),
    })
    tableau = pd.DataFrame({
        nom: mesures(previsions["reel"], previsions[colonne], froid)
        for nom, colonne in [("Modèle en V", "modele_v"), ("Droite unique", "droite"),
                             ("Climatologie", "climatologie")]
    }).T
    print(f"\n=== Test sur 2023 ({len(test)} jours, dont {froid.sum()} jours froids, "
          f"sous {seuil_froid:.1f} °C) ===")
    print(tableau.round(1).to_string())

    gain = 1 - tableau.loc["Modèle en V", "MAE (MW)"] / tableau.loc["Climatologie", "MAE (MW)"]
    print(f"\nLe modèle en V réduit l'erreur moyenne de {gain:.0%} par rapport à la climatologie.")

    previsions.to_csv(DOSSIER / "previsions_2023.csv", index=False)
    print(f"Prévisions enregistrées : {DOSSIER / 'previsions_2023.csv'}")


if __name__ == "__main__":
    main()