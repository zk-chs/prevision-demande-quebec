# Prévision de la demande d'électricité au Québec sur 7 jours

Outil de mesure statistique réalisé dans le cadre du cours INF-5103 – Concepts statistiques
pour la science des données (Université du Québec en Outaouais).

**Réalisateur :** Zakaria Chams-Eddine
**Client visé :** l'équipe qui planifie l'exploitation du réseau d'Hydro-Québec (client simulé)

## Ce que fait l'application

L'application prévoit la **demande moyenne journalière d'électricité du Québec** (en MW) pour
chacun des 7 jours d'une semaine, à partir de la température moyenne de Gatineau, Montréal et
Québec, et du jour de la semaine. Elle repose sur une régression en V : la demande augmente
fortement avec le froid sous 12,5 °C (chauffage) et plus faiblement avec la chaleur au-dessus
(climatisation).

Elle comporte trois onglets :

- **Prévision** : la demande prévue de chaque jour d'une semaine de 2019 à 2023, avec un
  intervalle à 90 %, la demande réelle, les jours de forte demande, et un scénario « et si »
  qui décale toutes les températures.
- **Comprendre le modèle** : la relation entre la demande et la température, et la signification
  de chaque coefficient.
- **Fiabilité** : les résultats du test sur l'année 2023 et les situations où l'outil doit être
  utilisé avec prudence.

## Lancer l'application

Prérequis : Python 3.12 et Git.

```bash
git clone https://github.com/zk-chs/prevision-demande-quebec.git
cd prevision-demande-quebec
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Puis la commande unique qui lance l'application :

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur à l'adresse http://localhost:8501. Elle fonctionne sans
connexion internet : les données nécessaires sont incluses dans le dépôt.

## Reproduire l'analyse

Les données traitées et les figures sont déjà dans le dépôt. Pour tout refaire depuis les données
brutes, exécuter les scripts dans cet ordre, depuis la racine du projet :

| Étape | Script | Rôle |
| --- | --- | --- |
| 1 | `src/telecharger_demande.py` | Télécharge la demande horaire d'Hydro-Québec (2019 à 2023) |
| 2 | `src/telecharger_meteo.py` | Télécharge les températures quotidiennes de six stations |
| 3 | `src/nettoyer_demande.py` | Calcule la demande moyenne des jours complets |
| 4 | `src/nettoyer_meteo.py` | Assemble les températures, avec stations de secours |
| 5 | `src/construire_donnees.py` | Fusionne les données et ajoute la température moyenne et le jour |
| 6 | `src/explorer_donnees.py` | Produit les graphiques d'exploration |
| 7 | `src/selectionner_modele.py` | Choisit le modèle sur l'année de validation 2022 |
| 8 | `src/evaluer_modele.py` | Ajuste le modèle sur 2019-2022 et le teste sur 2023 |
| 9 | `src/analyser_erreurs.py` | Analyse les erreurs de 2023 |
| 10 | `src/intervalles.py` | Calcule les intervalles à 90 % et leur couverture |

Exemple : `python src/evaluer_modele.py`. Les étapes 1 et 2 demandent une connexion internet.

## Structure du dépôt

```
app.py                 application Streamlit
src/                   scripts de collecte, de traitement et de modélisation
src/modele.py          définition du modèle, utilisée par les scripts et l'application
data/raw/              données brutes, jamais modifiées
data/processed/        données traitées, produites par les scripts
figures/               figures du rapport
requirements.txt       bibliothèques Python nécessaires
```

## Sources des données

- Hydro-Québec, *Historique de la demande d'électricité au Québec*, données ouvertes,
  licence CC-BY-NC 4.0 :
  https://www.hydroquebec.com/documents-data/open-data/history-electricity-demand-quebec/
- Environnement et Changement climatique Canada, *Données climatiques historiques* :
  https://climate.weather.gc.ca/