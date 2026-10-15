# ORBITALIS-DATA-CENTER

L’ordre pour tout lancer

`python etl/run_etl.py`

`# python etl/load.py`

`# python sql/run_requetes.py`

# ORBITALIS – Data Center en orbite

## 1. Le projet en quelques mots

ORBITALIS exploite un datacenter placé en **orbite basse (LEO, 550 km)**. Son électricité vient de **panneaux solaires**, puis passe par des **convertisseurs** et des **batteries**.

En orbite, les équipements subissent :

-   l'alternance **ensoleillement / éclipse** (la station passe dans l'ombre de la Terre),
-   des températures extrêmes (de -75 °C à +18 °C dehors),
-   le rayonnement,
-   le vieillissement progressif,
-   des pannes de capteurs ou de convertisseurs.

Une intervention de maintenance coûte cher et se planifie difficilement. Ce projet construit donc une **chaîne Data** qui :

1.  **fiabilise** les données brutes (ETL + contrôles qualité),
2.  les **range** dans deux bases SQLite (modèle conceptuel + modèle en étoile),
3.  les **analyse** en SQL (production, performances, pertes, alarmes, maintenance),
4.  **anticipe** les dégradations avec un modèle de maintenance prédictive.

> Règle d'or du projet : **une éclipse n'est jamais une panne.** Une puissance nulle à l'ombre est normale. Le contexte orbital (`orbite.csv`) est toujours utilisé pour distinguer une situation normale d'une anomalie.

---

## 2. L'application en un schéma

```
 data/raw/                  etl/                     data/cleaned/           data/db/
 (sources brutes)  ──►  extract → transform  ──►   (données propres)  ──►  orbitalis_conceptuel.db
 7 sources              → quality (contrôles)      data/analytics/         orbitalis_etoile.db
                                │                  (mesures enrichies)            │
                                ▼                                                 ▼
                         data/rejets/                                     sql/  → docs/resultats_requetes.md
                         data/quality/                                    ML/   → maintenance prédictive
```

---

## 3. Les données

### 3.1 Les sources (`data/raw/`)

Données **synthétiques**, sur 45 jours (du 2025-05-01 au 2025-06-14), avec des problèmes de qualité ajoutés volontairement.

Source

Contenu

Grain (une ligne =)

Clé

`sites.csv`

les 4 stations (Alpha, Beta, Gamma, Delta)

une station

`site_id`

`equipements.csv`

le matériel installé

un équipement

`equipement_id`

`telemetrie.csv`

les capteurs : puissance, température, tension, courant, rayonnement

1 équipement × 5 min

`(timestamp, equipement_id)`

`orbite.csv`

la phase orbitale, le rayonnement solaire, la température ambiante

1 station × 15 min

`(timestamp, site_id)`

`alarmes.json`

les incidents (6 types, 3 sévérités)

une alarme

`alarme_id`

`maintenance.csv`

les interventions (début, fin, type, coût)

une intervention

`maintenance_id`

`catalogue.db`

les modèles d'équipements, les seuils d'alarme, les références des sites

une référence

selon la table

### 3.2 Les relations

```
site 1 ──── n equipement 1 ──── n mesure (telemetrie)
  │                       ├──── n alarme      n ──── 1 type_alarme (seuils)
  │                       └──── n intervention (maintenance)
  │         equipement n ──── 1 modele (catalogue)
  └──── n etat_orbital (orbite)
```

La télémétrie est reliée à l'orbite par **le site et le créneau de 15 minutes**. C'est ce lien qui donne à chaque mesure sa phase (ensoleillement / éclipse).

### 3.3 Composition de chaque station

Chaque station a la même composition : 6 panneaux solaires, 3 batteries, 3 convertisseurs DC, 2 onduleurs et 2 radiateurs.

### 3.4 Résultat du nettoyage

Source

Lues

Acceptées

Rejetées

Doublons

sites

4

4

0

0

equipements

67

65

2

1

orbite

17 280

17 280

0

0

telemetrie

635 340

622 080

13 260

13 260

alarmes

521

520

1

1

maintenance

97

95

2

0

catalogues

22

22

0

0

---

## 4. Les étapes

### Étape 1 – Exploration

`etl/exploration.py` profile chaque source : structure, volume, types, valeurs manquantes, doublons, formats de dates et intégrité référentielle. La synthèse est dans `docs/synthese_exploration.md`.

### Étape 2 – ETL et qualité (raw → cleaned → analytics)

`etl/run_etl.py` orchestre la chaîne. Pour chaque source :

1.  **Harmonisation** : noms de colonnes en snake_case, types forcés, dates converties en **UTC, au format ISO 8601**. Une cascade de formats explicites gère les dates hétérogènes (`2025/05/01 10h30`, `01/05/2025`…).
2.  **Valeurs aberrantes** : une valeur hors des bornes physiques (`config.BORNES`) ou hors des modalités connues (`config.MODALITES`) est neutralisée (mise à vide) et comptée dans `data/quality/neutralisations.csv`. La ligne est conservée.
3.  **Contrôles et rejets** : ligne vide, clé nulle, date illisible, date hors période, intervalle de maintenance invalide, doublon, clé étrangère invalide. Chaque ligne rejetée part dans `data/rejets/rejets.csv` avec un **motif codé** (`CLE_DUPLIQUEE`, `FK_INVALIDE`…).
4.  **Contexte orbital** : chaque mesure de télémétrie reçoit la phase de son créneau de 15 minutes (`ensoleillement`, `eclipse`, ou `indetermine` si l'orbite est inconnue).
5.  **Zone analytics** : `data/analytics/mesures_enrichies.csv` ajoute aux mesures l'équipement, le site et deux indicateurs calculés :
    -   `puissance_attendue_w = puissance_nominale_w × rayonnement` (panneaux uniquement)
    -   `performance = puissance_reelle / puissance_attendue`
    -   `ecart_w = puissance_reelle - puissance_attendue`
6.  **Indicateurs qualité** par source dans `data/quality/indicateurs_par_source.csv`.

### Étape 3 – Modélisation et chargement

`etl/load.py` charge les données dans deux bases SQLite (`data/db/`).

**Modèle conceptuel** (`orbitalis_conceptuel.db`, schéma `modele/conceptuel.sql`, image `conceptuel.png`) Les données propres, normalisées, avec les clés métier : `site`, `equipement`, `modele`, `mesure`, `etat_orbital`, `alarme`, `type_alarme`, `intervention`.

**Modèle en étoile** (`orbitalis_etoile.db`, schéma `modele/etoile.sql`, image `etoil.png`) Les données prêtes pour l'analyse, avec des clés techniques entières :

Type

Tables

Dimensions

`dim_temps`, `dim_site`, `dim_equipement`, `dim_modele`, `dim_phase`, `dim_type_alarme`

Faits

`fait_mesure` (1 équipement × 5 min), `fait_alarme`, `fait_maintenance`

Mesures de `fait_mesure` : puissance, température, tension, courant, rayonnement, puissance attendue, performance, écart, **énergie (Wh)**, énergie attendue, **perte (Wh)**.

**Intégration du contexte orbital** : `dim_phase.production_attendue` vaut `1` en ensoleillement, `0` en éclipse et `NULL` si la phase est indéterminée. Les performances et les pertes ne sont calculées que là où une production est attendue. Une éclipse n'est donc jamais comptée comme une panne.

Au chargement, les contraintes du modèle (`NOT NULL`, clés étrangères) sont vérifiées. Les lignes qui les enfreignent sont tracées dans `data/rejets/rejets_chargement.csv`.

### Étape 4 – SQL et analyse

`sql/analyse.sql` contient les 9 requêtes du brief (production par jour, performances hors éclipse, alarmes par sévérité, délai entre maintenances, équipements non maintenus depuis 90 jours, pertes par site, évolution avec des fonctions de fenêtre, ensoleillement contre éclipse, coût des pertes non anticipées). `sql/run_requetes.py` les exécute toutes et écrit les résultats dans `docs/resultats_requetes.md`.

**Optimisation** : la requête qui filtre `fait_mesure` sur un équipement fait un `SCAN` des 622 080 lignes. L'index `(id_equipement, id_temps)` la transforme en `SEARCH`, qui ne lit plus que les ~9 700 lignes de l'équipement (`EXPLAIN QUERY PLAN`).

### Étape 5 – Maintenance prédictive

Le dossier `ML/` estime, à une date t, si un équipement risque d'entrer dans un état dégradé dans les **9 prochaines heures**. Le jeu est découpé **dans le temps**, jamais au hasard. On compare une régression logistique et un Random Forest, et le seuil de décision est choisi sur la validation pour **minimiser le coût métier** :

Situation

Coût

Dégradation non anticipée

2 500 €

Inspection inutile

150 €

Dégradation correctement anticipée

300 €

Pas de dégradation / pas d'inspection

0 €

---

## 5. Les fichiers et leur rôle

```
ORBITALIS/
├── config.py                  paramètres communs : chemins, bornes physiques, modalités,
│                              formats de dates, période, motifs de rejet
├── data/
│   ├── raw/                   sources brutes, jamais modifiées
│   ├── cleaned/               données propres, une source = un CSV
│   ├── analytics/             mesures_enrichies.csv (mesures + contexte + indicateurs)
│   ├── rejets/                rejets.csv (ETL) et rejets_chargement.csv (chargement)
│   ├── quality/               indicateurs par source, valeurs neutralisées
│   └── db/                    orbitalis_conceptuel.db et orbitalis_etoile.db
├── etl/
│   ├── exploration.py         profilage des 7 sources (étape 1)
│   ├── extract.py             lecture CSV / JSON / SQLite
│   ├── transform.py           harmonisation, dates UTC, bornes, contexte orbital, analytics
│   ├── quality.py             contrôles et séparation acceptées / rejetées
│   ├── run_etl.py             orchestration raw → cleaned → analytics
│   └── load.py                chargement des deux bases SQLite
├── modele/
│   ├── conceptuel.sql         schéma du modèle conceptuel
│   └── etoile.sql             schéma du modèle en étoile
├── conceptuel.png             diagramme du modèle conceptuel
├── etoil.png                  diagramme du modèle en étoile
├── sql/
│   ├── analyse.sql            les 9 requêtes d'analyse
│   └── run_requetes.py        exécution des requêtes et export Markdown
├── ML/
│   ├── Preparation.py         lecture de la base en étoile, construction du jeu d'entraînement
│   ├── Train.py               entraînement et comparaison des modèles, choix du seuil
│   ├── Prediction.py          calcul des scores de risque par équipement
│   └── MLOPS.py               sauvegarde et suivi des modèles
└── docs/
    ├── synthese_exploration.md   synthèse de l'exploration
    └── resultats_requetes.md     résultats des requêtes SQL
```

---

## 6. Lancer le projet

Installer les dépendances :

```bash
pip install pandas numpy scikit-learn
```

Lancer la chaîne dans l'ordre :

```bash
python etl/exploration.py
python etl/run_etl.py
python etl/load.py
python sql/run_requetes.py
```

Commande

Produit

`etl/exploration.py`

le profil des sources, dans la console

`etl/run_etl.py`

`data/cleaned/`, `data/analytics/`, `data/rejets/`, `data/quality/`

`etl/load.py`

`data/db/orbitalis_conceptuel.db` et `data/db/orbitalis_etoile.db`

`sql/run_requetes.py`

`docs/resultats_requetes.md`

La chaîne est **reproductible** : chaque script recrée ses sorties à chaque exécution.

---

## 7. Hypothèses documentées

-   Tous les horodatages sont supposés en **UTC** (aucune source n'indique de fuseau).
-   Une mesure de télémétrie représente **5 minutes** : `énergie_Wh = puissance_W × 5/60`.
-   Seuls les **panneaux solaires** sont des producteurs.
-   En **éclipse**, aucune production n'est attendue : ce n'est pas une anomalie.
-   Une **perte** est comptée seulement si elle est positive, c'est-à-dire si l'équipement a produit moins que prévu.
-   Une perte **non anticipée** survient en ensoleillement, hors période de maintenance.
-   Le prix de l'énergie est fixé à **0,15 €/kWh** (paramètre de la requête Q9).
-   Pour la question des 90 jours, la date de référence est la **dernière mesure disponible**.