# Application : prévision de la demande d'électricité au Québec sur 7 jours.
# Lancement : streamlit run app.py

import sys
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE / "src"))  # pour importer le modèle depuis src/
from modele import T0, ajuster, prevoir  # noqa: E402
from evaluer_modele import PART_FROIDE, mesures  # noqa: E402

DOSSIER = RACINE / "data" / "processed"
DOSSIER_FIGURES = RACINE / "figures"
T0_TEXTE = f"{T0:.1f}".replace(".", ",")  # « 12,5 », à la française
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


@st.cache_data
def charger_donnees() -> pd.DataFrame:
    """Le jeu de données journalier, 2019 à 2023."""
    return pd.read_csv(DOSSIER / "donnees_journalieres.csv", parse_dates=["date"])


@st.cache_resource
def modele_livre():
    """Le modèle livré, réajusté sur toutes les données disponibles (2019 à 2023)."""
    return ajuster(charger_donnees())


@st.cache_data
def charger_bornes() -> pd.DataFrame:
    """Les bornes de l'intervalle à 90 %, pour les jours froids et les jours doux."""
    return pd.read_csv(DOSSIER / "bornes_intervalle.csv", index_col="saison")


def seuil_forte_demande() -> float:
    """Une demande est « forte » si elle dépasse celle de 90 % des jours de 2019 à 2023."""
    return charger_donnees()["demande_mw"].quantile(0.90)


def prevoir_semaine(semaine: pd.DataFrame, decalage: float = 0) -> pd.DataFrame:
    """Ajoute à chaque jour sa prévision et son intervalle à 90 %, avec un décalage de température."""
    bornes = charger_bornes()
    p = semaine.copy()
    p["temp_moyenne"] = p["temp_moyenne"] + decalage
    p["prevision"] = prevoir(modele_livre(), p)
    saison = (p["temp_moyenne"] < T0).map({True: "froid", False: "doux"})
    p["borne_basse"] = p["prevision"] + saison.map(bornes["borne_basse"])
    p["borne_haute"] = p["prevision"] + saison.map(bornes["borne_haute"])
    return p


def etiquettes(p: pd.DataFrame) -> list[str]:
    """Étiquettes courtes des jours, par exemple « mer 01/02 »."""
    return [f"{JOURS[d.weekday()][:3]} {d:%d/%m}" for d in p["date"]]


def graphique_semaine(p: pd.DataFrame, base: pd.DataFrame | None) -> plt.Figure:
    """La demande prévue, son intervalle, la prévision sans décalage et la demande réelle."""
    fig, ax = plt.subplots(figsize=(7, 3.2))
    x = etiquettes(p)
    ax.fill_between(x, p["borne_basse"], p["borne_haute"], alpha=0.3, label="Intervalle à 90 %")
    ax.plot(x, p["prevision"], marker="o", label="Demande prévue")
    if base is not None:
        ax.plot(x, base["prevision"], linestyle="--", color="grey", label="Prévision sans décalage")
    if "demande_mw" in p:
        ax.plot(x, p["demande_mw"], marker="s", color="black", label="Demande réelle")
    ax.axhline(seuil_forte_demande(), color="red", linewidth=0.8, linestyle=":",
               label="Seuil de forte demande")
    ax.set_ylabel("Demande moyenne du jour (MW)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def mw(valeur: float) -> str:
    """Formate une puissance à la française : « 29 088 MW »."""
    return f"{valeur:,.0f} MW".replace(",", " ")


def onglet_prevision() -> None:
    donnees = charger_donnees()
    debut = st.date_input("Premier jour de la semaine", value=date(2023, 2, 1),
                          min_value=date(2019, 1, 1), max_value=date(2023, 12, 25))
    decalage = st.slider("Scénario « et si » : décalage de toutes les températures (°C)",
                         min_value=-10, max_value=10, value=0)

    fin = debut + timedelta(days=7)
    semaine = donnees[(donnees["date"].dt.date >= debut) & (donnees["date"].dt.date < fin)]
    if len(semaine) < 7:
        st.warning("Certains jours de cette semaine manquent dans les données. Choisissez une autre date.")
        return

    p = prevoir_semaine(semaine, decalage)
    base = prevoir_semaine(semaine) if decalage != 0 else None
    forts = p["prevision"] > seuil_forte_demande()
    pointe = p.loc[p["prevision"].idxmax()]

    colonne1, colonne2, colonne3 = st.columns(3)
    colonne1.metric(f"Pointe : {JOURS[pointe['date'].weekday()]} {pointe['date']:%d/%m}",
                    mw(pointe["prevision"]))
    colonne2.metric("Demande moyenne prévue", mw(p["prevision"].mean()))
    colonne3.metric("Jours de forte demande", f"{forts.sum()} sur 7")

    st.pyplot(graphique_semaine(p, base))

    tableau = pd.DataFrame({
        "Date": p["date"].dt.strftime("%Y-%m-%d"),
        "Jour": [JOURS[d.weekday()] for d in p["date"]],
        "Température (°C)": p["temp_moyenne"].round(1),
        "Demande prévue (MW)": p["prevision"].round(0),
        "Intervalle à 90 % (MW)": [f"{mw(b)[:-3]} à {mw(h)}"
                                   for b, h in zip(p["borne_basse"], p["borne_haute"])],
        "Demande réelle (MW)": p["demande_mw"].round(0),
        "Alerte": ["Forte demande" if f else "" for f in forts],
    })
    st.dataframe(tableau, hide_index=True)

    st.caption(f"Forte demande : au-dessus de {mw(seuil_forte_demande())}, valeur dépassée par 10 % "
               "des jours de 2019 à 2023. Le modèle de l'application a été ajusté sur toutes les "
               "données de 2019 à 2023, y compris cette semaine : pour une évaluation sur des jours "
               "inconnus du modèle, voir l'onglet Fiabilité.")


def graphique_modele() -> plt.Figure:
    """La crosse de hockey des données, avec les deux droites du modèle en V."""
    donnees, modele = charger_donnees(), modele_livre()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.scatter(donnees["temp_moyenne"], donnees["demande_mw"], s=4, alpha=0.25, color="grey",
               label="Jours de 2019 à 2023")
    temperatures = np.linspace(donnees["temp_moyenne"].min(), donnees["temp_moyenne"].max(), 200)
    for jour, nom, couleur in [("mardi", "lundi à jeudi", "tab:blue"),
                               ("dimanche", "fin de semaine", "tab:orange")]:
        grille = pd.DataFrame({"date": donnees["date"].max(), "temp_moyenne": temperatures,
                               "jour_semaine": jour})
        ax.plot(temperatures, prevoir(modele, grille), color=couleur, label=f"Modèle, {nom}")
    ax.axvline(T0, color="black", linewidth=0.8, linestyle="--", label=f"Seuil T0 = {T0_TEXTE} °C")
    ax.set_xlabel("Température moyenne des trois villes (°C)")
    ax.set_ylabel("Demande moyenne du jour (MW)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def onglet_comprendre() -> None:
    modele = modele_livre()
    params, ic = modele.params, modele.conf_int()
    st.markdown(
        f"La demande dépend surtout de la température. Sous **{T0_TEXTE} °C**, plus il fait froid, "
        "plus on chauffe : la demande monte fortement. Au-dessus, elle monte plus faiblement "
        "avec la chaleur (climatisation). La fin de semaine, la demande est plus basse, "
        "car les bureaux et une partie de l'industrie fonctionnent moins.")
    st.pyplot(graphique_modele())
    st.caption("Les droites du modèle sont tracées au niveau de demande de la fin de 2023 : "
               "les jours plus anciens se trouvent en moyenne un peu en dessous, à cause de la "
               "croissance de la demande.")

    effets = [  # (nom affiché, nom du coefficient, unité, signification)
        ("Chauffage", "chauffage", "MW par degré", "Hausse de la demande pour chaque degré sous le seuil"),
        ("Climatisation", "climatisation", "MW par degré", "Hausse pour chaque degré au-dessus du seuil"),
        ("Tendance", "tendance", "MW par an", "Croissance annuelle de la demande, à météo égale"),
        ("Vendredi", "vendredi", "MW", "Écart avec un jour du lundi au jeudi"),
        ("Fin de semaine", "fin de semaine", "MW", "Écart avec un jour du lundi au jeudi"),
    ]
    st.dataframe(pd.DataFrame({
        "Effet": [nom for nom, _, _, _ in effets],
        "Valeur": [f"{params[c]:+,.0f} {unite}".replace(",", " ") for _, c, unite, _ in effets],
        "Intervalle de confiance à 95 %": [f"{ic.loc[c, 0]:,.0f} à {ic.loc[c, 1]:,.0f}".replace(",", " ")
                                          for _, c, _, _ in effets],
        "Signification": [sens for _, _, _, sens in effets],
    }), hide_index=True)

    st.info(f"Exemple : une baisse de 10 °C sous le seuil ajoute environ "
            f"{mw(10 * params['chauffage'])} à la demande moyenne du jour.")
    st.caption("Coefficients du modèle livré, ajusté sur 2019 à 2023. Le rapport présente ceux du "
               "modèle évalué, ajusté sur 2019 à 2022.")


# ---------------------------------------------------------------- Interface
@st.cache_data
def charger_previsions_2023() -> pd.DataFrame:
    """Les prévisions de l'année de test 2023 (modèle ajusté sur 2019-2022, voir evaluer_modele.py)."""
    return pd.read_csv(DOSSIER / "previsions_2023.csv", parse_dates=["date"])


def onglet_fiabilite() -> None:
    p = charger_previsions_2023()
    froid = p["temp_moyenne"] <= p["temp_moyenne"].quantile(PART_FROIDE)
    resultats = pd.DataFrame({
        nom: mesures(p["reel"], p[colonne], froid)
        for nom, colonne in [("Modèle en V", "modele_v"), ("Droite unique", "droite"),
                             ("Climatologie", "climatologie")]
    }).T

    st.markdown("Le modèle a été évalué sur l'année **2023**, qu'il n'avait jamais vue : il a été "
                "ajusté sur 2019 à 2022, puis comparé à la **climatologie**, c'est-à-dire la demande "
                "moyenne des années passées pour le même mois et le même type de jour, ce qu'un "
                "planificateur prévoirait sans outil.")

    modele, climato = resultats.loc["Modèle en V"], resultats.loc["Climatologie"]
    ecart = (modele / climato - 1) * 100  # écart en % avec la climatologie
    colonne1, colonne2 = st.columns(2)
    colonne1.metric("Erreur moyenne en 2023", mw(modele["MAE (MW)"]),
                    f"{ecart['MAE (MW)']:.0f} % par rapport à la climatologie", delta_color="inverse")
    colonne2.metric("Erreur moyenne des jours les plus froids", mw(modele["MAE jours froids (MW)"]),
                    f"{ecart['MAE jours froids (MW)']:.0f} % par rapport à la climatologie",
                    delta_color="inverse")

    st.dataframe(resultats.round(1), column_config={"_index": "Modèle"})
    st.caption("Jours froids : les 10 % de jours les plus froids de 2023. "
               "Biais positif : le modèle sous-estime la demande ; négatif : il la surestime.")

    st.image(str(DOSSIER_FIGURES / "reel_prevu_2023.png"),
             caption="Demande réelle et prévision du modèle, jour par jour, en 2023.")
    st.image(str(DOSSIER_FIGURES / "erreur_selon_horizon.png"),
             caption="Erreur de l'outil quand la température est une prévision météo, selon l'horizon.")

    st.subheader("Quand faire confiance à l'outil")
    st.success("**En hiver, sur les 7 jours.** L'outil est le plus utile lors des grands froids. "
               "Même avec une prévision météo à 7 jours, son erreur sur les jours froids reste "
               "inférieure à celle de la climatologie.")
    st.warning("**En saison douce, au-delà de 4 jours.** La demande dépend alors peu de la "
               "température, et l'outil ne fait pas mieux qu'une moyenne historique. En 2023, il a "
               "aussi surestimé la demande des mois doux, jusqu'à environ 1 100 MW en octobre, et son "
               "intervalle à 90 % y sous-estime l'incertitude.")
    st.warning("**Au début et à la fin d'une vague de froid, et les jours fériés.** L'outil ignore "
               "l'inertie thermique des bâtiments et ne distingue pas les jours fériés, qui se "
               "comportent comme une fin de semaine.")
    st.info("**Mettre à jour le modèle régulièrement.** Ses données s'arrêtent fin 2023 ; le "
            "réajuster avec les données récentes recale le niveau de la demande, ce qui devrait "
            "réduire le biais observé pendant les mois doux.")
    
st.set_page_config(page_title="Prévision de la demande d'électricité")
st.title("Prévision de la demande d'électricité au Québec sur 7 jours")
st.caption("Modèle en V : demande selon la température moyenne de Gatineau, Montréal "
           "et Québec, et le jour de la semaine.")

prevision, comprendre, fiabilite = st.tabs(["Prévision", "Comprendre le modèle", "Fiabilité"])
with prevision:
    onglet_prevision()
with comprendre:
    onglet_comprendre()
with fiabilite:
    onglet_fiabilite()