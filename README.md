# ORBITALIS Data Center

## Le projet

ORBITALIS exploite un datacenter placé en orbite basse, à 550 km d'altitude

Son électricité vient de panneaux solaires, puis passe par des convertisseurs et des batteries

En orbite, les équipements subissent
- l'alternance entre ensoleillement et éclipse, quand la station passe dans l'ombre de la Terre
- des températures extrêmes, de moins 75 °C à plus 18 °C à l'extérieur
- le rayonnement
- le vieillissement progressif
- des pannes de capteurs ou de convertisseurs

Les interventions de maintenance coûtent cher et se planifient difficilement

Ce projet construit une chaîne Data qui
- fiabilise les données brutes
- range les données dans deux bases SQLite, un modèle conceptuel et un modèle en étoile
- analyse les performances en SQL
- anticipe les dégradations des panneaux avec un modèle de maintenance prédictive

La règle d'or du projet est simple, une éclipse n'est jamais une panne

Une puissance nulle à l'ombre est normale, le contexte orbital sert toujours à distinguer une situation normale d'une anomalie

## Les données

Les données sont synthétiques et couvrent 45 jours, du 1er mai au 14 juin 2025

Des problèmes de qualité y ont été ajoutés volontairement, comme des dates dans des formats différents, des doublons, des valeurs aberrantes ou des clés invalides

| Source | Contenu | Une ligne correspond à |
|---|---|---|
| sites.csv | les 4 stations Alpha, Beta, Gamma et Delta | une station |
| equipements.csv | le matériel installé | un équipement |
| telemetrie.csv | puissance, température, tension, courant et rayonnement | un équipement toutes les 5 minutes |
| orbite.csv | la phase orbitale et le rayonnement solaire | une station toutes les 15 minutes |
| alarmes.json | les incidents, 6 types et 3 niveaux de sévérité | une alarme |
| maintenance.csv | les interventions avec début, fin, type et coût | une intervention |
| catalogue.db | les modèles d'équipements, les seuils d'alarme et les références des sites | une référence |

Chaque station contient 6 panneaux solaires, 3 batteries, 3 convertisseurs, 2 onduleurs et 2 radiateurs

Une orbite dure 2 heures dans ces données, avec 75 minutes de soleil puis 45 minutes d'éclipse

### Les relations entre les sources

- un site possède plusieurs équipements
- un équipement produit plusieurs mesures, alarmes et interventions
- un équipement correspond à un modèle du catalogue
- un site possède un état orbital toutes les 15 minutes

Une mesure de télémétrie est reliée à l'orbite par son site et par son créneau de 15 minutes, c'est ce lien qui lui donne sa phase

### Résultat du nettoyage

| Source | Lues | Acceptées | Rejetées | Doublons |
|---|---|---|---|---|
| sites | 4 | 4 | 0 | 0 |
| equipements | 67 | 65 | 2 | 1 |
| orbite | 17 280 | 17 280 | 0 | 0 |
| telemetrie | 635 340 | 622 080 | 13 260 | 13 260 |
| alarmes | 521 | 520 | 1 | 1 |
| maintenance | 97 | 95 | 2 | 0 |
| catalogues | 22 | 22 | 0 | 0 |

## Les étapes

### Étape 1, exploration

Le script etl/exploration.py étudie chaque source, sa structure, son volume, ses types, ses valeurs manquantes, ses doublons, ses formats de dates et ses liens avec les autres sources

La synthèse se trouve dans docs/synthese_exploration.md

### Étape 2, ETL et qualité

Le script etl/run_etl.py fait passer les données de raw vers cleaned puis vers analytics

Pour chaque source
- les noms de colonnes sont harmonisés
- les dates sont converties en UTC au format ISO 8601
- les valeurs hors des bornes physiques ou des modalités connues sont vidées et comptées
- les lignes vides, les clés nulles, les dates illisibles, les doublons et les clés étrangères invalides sont rejetées avec un motif
- chaque mesure de télémétrie reçoit sa phase orbitale, ensoleillement, éclipse ou indéterminée

La zone analytics ajoute deux indicateurs calculés

- puissance attendue égale à la puissance nominale multipliée par le rayonnement
- performance égale à la puissance réelle divisée par la puissance attendue

Les lignes rejetées sont gardées dans data/rejets et les indicateurs de qualité dans data/quality

### Étape 3, modélisation et chargement

Le script etl/load.py charge deux bases SQLite dans data/db

La base orbitalis_conceptuel.db contient les données propres, avec les tables site, equipement, modele, mesure, etat_orbital, alarme, type_alarme et intervention

La base orbitalis_etoile.db contient les données prêtes pour l'analyse

| Type | Tables |
|---|---|
| Dimensions | dim_temps, dim_site, dim_equipement, dim_modele, dim_phase, dim_type_alarme |
| Faits | fait_mesure, fait_alarme, fait_maintenance |

La table fait_mesure contient la puissance, la température, la tension, le courant, le rayonnement, la puissance attendue, la performance, l'énergie produite, l'énergie attendue et la perte

La table dim_phase indique si une production est attendue, oui en ensoleillement, non en éclipse

Les performances et les pertes ne sont calculées que lorsque une production est attendue

Les schémas sont dans modele/conceptuel.sql et modele/etoile.sql, et les diagrammes dans conceptuel.png et etoil.png

### Étape 4, SQL et analyse

Le fichier sql/analyse.sql contient les 9 requêtes du brief
- production totale par équipement et par jour
- équipements les moins performants hors éclipse
- nombre d'alarmes par équipement et par sévérité
- délai moyen entre deux maintenances
- équipements non maintenus depuis plus de 90 jours
- perte de production par site en kWh
- évolution de la performance avec des fonctions de fenêtre
- comparaison entre ensoleillement et éclipse
- coût des pertes de production non anticipées

Le script sql/run_requetes.py exécute toutes les requêtes et écrit les résultats dans docs/resultats_requetes.md

Pour l'optimisation, une requête qui filtre fait_mesure sur un seul équipement lit les 622 080 lignes

Un index sur id_equipement et id_temps lui permet de ne lire que les lignes de cet équipement, et la requête passe de 102 ms à 7 ms

### Étape 5, maintenance prédictive

Le but est de prévoir, pour chaque panneau solaire, s'il sera à risque dans les 12 prochaines heures, soit 6 périodes orbitales

Un panneau est à risque si, dans les 12 heures suivantes
- sa performance au soleil passe sous 0,65
- ou il déclenche une alarme critique liée à la puissance ou à la température

Le fichier ML/Preparation.py lit la base conceptuelle et construit les variables, en gardant uniquement les mesures au soleil

| Variable | Signification |
|---|---|
| puissance_w | puissance mesurée |
| rayonnement | rayonnement reçu |
| temperature_c | température |
| tension_v | tension |
| courant_a | courant |
| puissance_nominale_w | puissance du modèle de panneau |
| age_jours | âge depuis l'installation |
| puissance_moyenne_24h | production moyenne des 24 dernières heures |
| tendance_24h | évolution par rapport à la veille, négative si le panneau se dégrade |
| alarmes_24h | nombre d'alarmes des 24 dernières heures |
| heures_depuis_maintenance | temps écoulé depuis la dernière intervention |

Les variables regardent uniquement le passé et la cible regarde uniquement le futur, pour éviter toute fuite de données

Le fichier ML/Train.py découpe les données dans le temps, sans jamais les mélanger

| Jeu | Période | Part à risque |
|---|---|---|
| train | du 1er au 30 mai | 17 % |
| validation | du 31 mai au 6 juin | 48 % |
| test | du 7 au 14 juin | 64 % |

La part à risque augmente parce que les panneaux se dégradent avec le temps

Deux modèles sont comparés, une régression logistique et un Random Forest

Résultats sur la validation avec un seuil de 0,5

| Score | Régression logistique | Random Forest |
|---|---|---|
| accuracy | 0,76 | 0,87 |
| precision | 0,68 | 0,94 |
| recall | 0,97 | 0,79 |
| f1 | 0,80 | 0,86 |
| roc auc | 0,97 | 0,96 |
| dégradations ratées | 355 | 2 790 |
| inspections inutiles | 6 271 | 738 |

Le Random Forest est presque parfait sur le train puis perd en recall sur la validation et le test, il apprend le train par cœur et ne sait pas prolonger la dégradation vers des niveaux jamais vus

La régression logistique généralise mieux et rate beaucoup moins de dégradations

Le coût métier du brief guide le choix du modèle

| Situation | Coût |
|---|---|
| dégradation non anticipée | 2 500 € |
| inspection inutile | 150 € |
| dégradation correctement anticipée | 300 € |
| pas de dégradation et pas d'inspection | 0 € |

Rater une panne coûte 17 fois plus cher qu'une inspection inutile, le meilleur modèle selon l'accuracy n'est donc pas le meilleur pour le métier

Le modèle retenu est sauvegardé dans model/modele_risque.joblib avec ses variables et son seuil

Les graphiques sont enregistrés dans le dossier graphique

## Organisation des fichiers

| Fichier ou dossier | Rôle |
|---|---|
| config.py | paramètres communs, chemins, bornes physiques, formats de dates et motifs de rejet |
| data/raw | sources brutes, jamais modifiées |
| data/cleaned | données propres, un fichier par source |
| data/analytics | mesures enrichies avec le contexte et les indicateurs |
| data/rejets | lignes rejetées par l'ETL et par le chargement |
| data/quality | indicateurs de qualité par source |
| data/db | bases SQLite conceptuelle et en étoile |
| etl/exploration.py | exploration des 7 sources |
| etl/extract.py | lecture des fichiers CSV, JSON et SQLite |
| etl/transform.py | harmonisation, dates, bornes, contexte orbital et indicateurs |
| etl/quality.py | contrôles et séparation des lignes acceptées et rejetées |
| etl/run_etl.py | orchestration de la chaîne ETL |
| etl/load.py | chargement des deux bases SQLite |
| modele | schémas SQL des deux modèles |
| sql/analyse.sql | les 9 requêtes d'analyse |
| sql/run_requetes.py | exécution des requêtes et export des résultats |
| ML/Preparation.py | lecture des données et construction des variables |
| ML/Train.py | cible, découpage, entraînement, scores, graphiques et sauvegarde du modèle |
| ML/Prediction.py | prévu pour calculer les scores de risque avec le modèle sauvegardé |
| ML/MLOPS.py | prévu pour le suivi des versions du modèle |
| model | modèle entraîné |
| graphique | graphiques des prédictions et des scores |
| docs | synthèse d'exploration et résultats des requêtes |

## Lancer le projet

Installer les dépendances

```bash
pip install pandas numpy scikit-learn matplotlib joblib
```

Lancer les scripts dans cet ordre depuis la racine du projet

```bash
python etl/exploration.py
python etl/run_etl.py
python etl/load.py
python sql/run_requetes.py
python ML/Train.py
```

| Script | Ce qu'il produit |
|---|---|
| etl/exploration.py | le profil des sources dans la console |
| etl/run_etl.py | data/cleaned, data/analytics, data/rejets et data/quality |
| etl/load.py | les deux bases dans data/db |
| sql/run_requetes.py | docs/resultats_requetes.md |
| ML/Train.py | les scores, les graphiques et model/modele_risque.joblib |

Chaque script recrée ses sorties, la chaîne est donc reproductible

## Hypothèses

- tous les horodatages sont considérés en UTC car aucune source n'indique de fuseau
- une mesure de télémétrie représente 5 minutes de production
- seuls les panneaux solaires produisent de l'énergie
- aucune production n'est attendue pendant une éclipse
- une orbite dure 2 heures, 6 périodes orbitales font donc 12 heures
- une perte n'est comptée que si l'équipement produit moins que prévu
- une perte non anticipée survient au soleil et hors période de maintenance
- le prix de l'énergie est fixé à 0,15 € par kWh
- pour la question des 90 jours, la date de référence est la dernière mesure disponible