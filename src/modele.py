# Le modèle de prévision retenu : une régression en V.
#
#   demande = constante + a × chauffage + b × climatisation + c × tendance + effet du jour
#
# Les choix (seuil T0, groupes de jours, tendance) ont été faits sur l'année
# de validation 2022, avec le script selectionner_modele.py.

import pandas as pd
import statsmodels.api as sm

T0 = 12.5                           # seuil de bascule, en température moyenne des trois villes
DEBUT = pd.Timestamp("2019-01-01")  # origine de la tendance

GROUPES = {"lundi": "lun-jeu", "mardi": "lun-jeu", "mercredi": "lun-jeu", "jeudi": "lun-jeu",
           "vendredi": "vendredi", "samedi": "fin de semaine", "dimanche": "fin de semaine"}
ORDRE_GROUPES = ["lun-jeu", "vendredi", "fin de semaine"]


def variables(donnees: pd.DataFrame) -> pd.DataFrame:
    """Construit les variables explicatives du modèle à partir de la date, de la température et du jour."""
    t = donnees["temp_moyenne"]
    X = pd.DataFrame({
        "chauffage": (T0 - t).clip(lower=0),                         # degrés sous T0
        "climatisation": (t - T0).clip(lower=0),                     # degrés au-dessus de T0
        "tendance": (donnees["date"] - DEBUT).dt.days / 365.25,      # années depuis 2019
    })
    groupes = pd.Categorical(donnees["jour_semaine"].map(GROUPES), categories=ORDRE_GROUPES)
    # Une indicatrice par groupe, sauf lundi-jeudi, qui sert de référence.
    indicatrices = pd.get_dummies(groupes, drop_first=True, dtype=float)
    indicatrices.index = donnees.index
    # has_constant="add" : la constante est ajoutée même pour quelques jours à prévoir.
    return sm.add_constant(pd.concat([X, indicatrices], axis=1), has_constant="add")


def ajuster(donnees: pd.DataFrame):
    """Ajuste le modèle par moindres carrés ordinaires."""
    return sm.OLS(donnees["demande_mw"], variables(donnees)).fit()


def prevoir(modele, donnees: pd.DataFrame) -> pd.Series:
    """Prévoit la demande des jours fournis."""
    return modele.predict(variables(donnees))