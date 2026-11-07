# Analyse des erreurs du modèle sur l'année de test 2023 :
# quand le modèle se trompe-t-il, et dans quel sens ?

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
FICHIER_PREVISIONS = RACINE / "data" / "processed" / "previsions_2023.csv"
DOSSIER_FIGURES = RACINE / "figures"
ARRONDIS = {"temp_moyenne": 1, "reel": 0, "modele_v": 0, "erreur": 0}  # décimales à l'affichage
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["jan", "fév", "mar", "avr", "mai", "juin", "juil", "août", "sep", "oct", "nov", "déc"]


def enregistrer(fig: plt.Figure, nom: str) -> None:
    """Enregistre une figure en image dans le dossier figures/."""
    chemin = DOSSIER_FIGURES / nom
    fig.tight_layout()
    fig.savefig(chemin, dpi=150)
    plt.close(fig)
    print(f"Figure enregistrée : {chemin}")


def figure_reel_prevu(p: pd.DataFrame) -> None:
    """La demande réelle et la prévision du modèle, jour par jour, en 2023."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(p["date"], p["reel"], linewidth=1, label="Demande réelle")
    ax.plot(p["date"], p["modele_v"], linewidth=1, label="Prévision du modèle")
    ax.set_title("Demande réelle et prévision du modèle en V, année de test 2023")
    ax.set_xlabel("Date")
    ax.set_ylabel("Demande (MW)")
    ax.legend()
    ax.grid(alpha=0.3)
    enregistrer(fig, "reel_prevu_2023.png")


def figure_erreur_mois(p: pd.DataFrame) -> None:
    """L'erreur moyenne et le biais du modèle, mois par mois."""
    mois = p["date"].dt.month
    par_mois = pd.DataFrame({
        "MAE": p["erreur"].abs().groupby(mois).mean(),
        "Biais": p["erreur"].groupby(mois).mean(),  # > 0 : sous-estimation
    })
    x = np.arange(12)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(x - 0.2, par_mois["MAE"], width=0.4, label="Erreur absolue moyenne")
    ax.bar(x + 0.2, par_mois["Biais"], width=0.4, label="Biais (> 0 : sous-estimation)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x, MOIS)
    ax.set_title("Erreurs du modèle par mois, année de test 2023")
    ax.set_ylabel("MW")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    enregistrer(fig, "erreur_par_mois_2023.png")

    print("  Erreurs par mois (MW) :")
    par_mois.index = MOIS
    print(par_mois.round(0).to_string())


def plus_grandes_erreurs(p: pd.DataFrame, nombre: int = 10) -> None:
    """Les jours où le modèle s'est le plus trompé."""
    pires = p.loc[p["erreur"].abs().nlargest(nombre).index].copy()
    pires["jour"] = [JOURS[i] for i in pires["date"].dt.day_of_week]
    colonnes = ["date", "jour", "temp_moyenne", "reel", "modele_v", "erreur"]
    print(f"\n  Les {nombre} plus grandes erreurs de 2023 :")
    print(pires[colonnes].round(ARRONDIS).to_string(index=False))


def main() -> None:
    p = pd.read_csv(FICHIER_PREVISIONS, parse_dates=["date"])
    p["erreur"] = p["reel"] - p["modele_v"]  # > 0 : le modèle sous-estime

    figure_reel_prevu(p)
    figure_erreur_mois(p)
    plus_grandes_erreurs(p)

    record = p[p["date"].isin(pd.to_datetime(["2023-02-03", "2023-02-04"]))]
    print("\n  Épisode de froid extrême de février 2023 :")
    colonnes = ["date", "temp_moyenne", "reel", "modele_v", "erreur"]
    print(record[colonnes].round(ARRONDIS).to_string(index=False))


if __name__ == "__main__":
    main()