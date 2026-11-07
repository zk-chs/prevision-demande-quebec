# Effet des erreurs de prévision météo sur la qualité de l'outil.
#
# Le test sur 2023 utilise les températures observées. En réalité, le client n'aura
# que des températures prévues, qui se trompent d'autant plus que l'horizon est lointain.
# On simule ces erreurs : pour chaque horizon de 1 à 7 jours, on ajoute à la température
# de chaque jour de 2023 une erreur aléatoire de loi normale, dont l'erreur absolue moyenne
# passe de 1,5 °C (1 jour) à 3,0 °C (7 jours), puis on mesure l'erreur de prévision de la demande.
# Hypothèse simplificatrice : les erreurs météo sont indépendantes d'un jour à l'autre.

from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from modele import ajuster, prevoir

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "data" / "processed"
FICHIER_FIGURE = RACINE / "figures" / "erreur_selon_horizon.png"
MAE_METEO_JOUR_1, MAE_METEO_JOUR_7 = 1.5, 3.0  # erreur absolue moyenne des prévisions météo (°C)
HORIZONS = range(1, 8)
SIMULATIONS = 200
PART_FROIDE = 0.10


def mae_meteo(horizon: int) -> float:
    """Erreur absolue moyenne de la température prévue, interpolée entre le jour 1 et le jour 7."""
    return MAE_METEO_JOUR_1 + (MAE_METEO_JOUR_7 - MAE_METEO_JOUR_1) * (horizon - 1) / 6


def main() -> None:
    donnees = pd.read_csv(DOSSIER / "donnees_journalieres.csv", parse_dates=["date"])
    previsions = pd.read_csv(DOSSIER / "previsions_2023.csv", parse_dates=["date"])
    modele = ajuster(donnees[donnees["date"].dt.year <= 2022])
    test = donnees[donnees["date"].dt.year == 2023].reset_index(drop=True)
    froid = test["temp_moyenne"] <= test["temp_moyenne"].quantile(PART_FROIDE)
    generateur = np.random.default_rng(42)  # graine fixée : résultats reproductibles

    lignes = []
    for horizon in [0, *HORIZONS]:  # horizon 0 : température parfaitement connue
        # Pour une loi normale, écart-type = erreur absolue moyenne × racine(pi / 2).
        ecart_type = 0 if horizon == 0 else mae_meteo(horizon) * np.sqrt(np.pi / 2)
        mae, mae_froid = [], []
        for _ in range(SIMULATIONS if horizon else 1):
            temperature_prevue = test["temp_moyenne"] + generateur.normal(0, ecart_type, len(test))
            erreur = test["demande_mw"] - prevoir(modele, test.assign(temp_moyenne=temperature_prevue))
            mae.append(erreur.abs().mean())
            mae_froid.append(erreur[froid].abs().mean())
        lignes.append({"horizon (jours)": horizon,
                       "erreur météo (°C)": 0 if horizon == 0 else mae_meteo(horizon),
                       "MAE (MW)": np.mean(mae),
                       "MAE jours froids (MW)": np.mean(mae_froid)})
    resultats = pd.DataFrame(lignes)

    climato = (previsions["reel"] - previsions["climatologie"]).abs()
    climato_mae, climato_froid = climato.mean(), climato[froid.values].mean()

    print(f"=== Erreur de l'outil selon l'horizon de prévision, 2023 ({SIMULATIONS} simulations) ===")
    print(resultats.round(1).to_string(index=False))
    print(f"\nClimatologie (non touchée par la météo) : MAE {climato_mae:.0f} MW, "
          f"jours froids {climato_froid:.0f} MW")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(resultats["horizon (jours)"], resultats["MAE (MW)"], marker="o", label="Modèle, tous les jours")
    ax.plot(resultats["horizon (jours)"], resultats["MAE jours froids (MW)"], marker="o",
            label="Modèle, jours froids")
    ax.axhline(climato_mae, linestyle="--", color="tab:blue", label="Climatologie, tous les jours")
    ax.axhline(climato_froid, linestyle="--", color="tab:orange", label="Climatologie, jours froids")
    ax.set_title("Erreur de prévision de la demande selon l'horizon, année de test 2023")
    ax.set_xlabel("Horizon de prévision (jours) ; 0 = température observée")
    ax.set_ylabel("Erreur absolue moyenne (MW)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FICHIER_FIGURE, dpi=150)
    plt.close(fig)
    print(f"Figure enregistrée : {FICHIER_FIGURE}")


if __name__ == "__main__":
    main()