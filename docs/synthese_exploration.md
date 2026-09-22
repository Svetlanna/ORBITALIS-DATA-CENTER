# synthèse d'exploration
Période couverte par les données : 2025-05-01 → 2025-06-14 (45 jours)


## sources disponibles et grain

| source | volume mesuré | grain, une ligne égale | clé |
|---|---|---|---|
| `sites.csv` | 5 lignes dont 4 sites réels | un site | `site_id` |
| `equipements.csv` | 68 lignes dont 66 équipements réels | un équipement | `equipement_id` |
| `telemetrie.csv` | 635 340 lignes, 48 équipements | une mesure, équipement × 5 min | `(timestamp, equipement_id)` |
| `orbite.csv` | 17 280 lignes, 4 sites × 4 320 pas | un état orbital, site × 15 min | `(timestamp, site_id)` |
| `alarmes.json` | 521 alarmes | un événement ponctuel | `alarme_id` |
| `maintenance.csv` | 97 interventions | un intervalle, début → fin | `maintenance_id` |
| `catalogue.db` | 12 modèles, 6 seuils, 4 sites | un référentiel | `modele_id`, `type_alarme`, `site_id` |

période couverte, du 2025-05-01 au 2025-06-14, soit 45 jours

les sources portent quatre notions de temps différentes — un pas de 5 minutes, un pas de
15 minutes, un événement instantané et un intervalle daté

aucune jointure temporelle ne peut être faite sans une règle de rapprochement explicite

### relations entre les sources

les sept sources forment une étoile autour de `equipements`, qui porte à la fois
la clé du site et la clé du modèle

| depuis | vers | clé | état |
|---|---|---|---|
| `telemetrie.equipement_id` | `equipements.equipement_id` | equipement_id | valide |
| `alarmes.equipement_id` | `equipements.equipement_id` | equipement_id | valide |
| `maintenance.equipement_id` | `equipements.equipement_id` | equipement_id | rompue sur les lignes `EQ-XXX` |
| `equipements.site_id` | `sites.site_id` | site_id | rompue sur les lignes `SITE-XXX` |
| `orbite.site_id` | `sites.site_id` | site_id | valide |
| `equipements.modele_id` | `catalogue.modeles.modele_id` | modele_id | rompue sur 65 modèles sur 66 |
| `alarmes.type_alarme` | `catalogue.seuils.type_alarme` | type_alarme | à vérifier, modalités hors référentiel |

deux chemins comptent plus que les autres

le premier relie une mesure à sa puissance de référence, `telemetrie` vers
`equipements` vers `catalogue.modeles`, et il est aujourd'hui coupé au dernier
maillon, ce qui bloque tout calcul de performance

le second relie une mesure à son contexte orbital, `telemetrie` vers
`equipements` vers `sites` vers `orbite`, et il impose un changement de grain
puisque la télémétrie est au pas de 5 min par équipement quand l'orbite est au
pas de 15 min par site


## données fiables et données problématiques

**fiables** — `orbite.csv` avec 17 280 lignes parfaitement réparties, une clé composite
valide, aucun doublon et 0,09 % de valeurs manquantes

`catalogue.references_sites` et `catalogue.seuils_alarmes` sont complets et cohérents

**problématiques** — `telemetrie.csv` avec 13 260 doublons de clé et des valeurs
physiquement impossibles, ainsi que `equipements.csv` avec une clé invalide, une
puissance nominale négative et des modalités illégales

**inutilisable en l'état** — la jointure `equipements.modele → catalogue.modeles` échoue
sur 65 modèles sur 66, elle bloque le calcul de la puissance attendue

### informations nécessaires pour analyser une dégradation

une dégradation est un écart entre ce qu'un équipement produit et ce qu'il
devrait produire dans les conditions du moment, six éléments sont donc
nécessaires

1. la puissance réelle mesurée — `telemetrie.puissance_w`, au pas de 5 min
2. la puissance attendue — `catalogue.modeles.puissance_nominale_w`, atteinte
   depuis `equipements.modele_id`, aujourd'hui inaccessible car la jointure est
   rompue sur 65 modèles sur 66
3. la phase orbitale — `orbite.phase`, atteinte depuis `equipements.site_id`,
   sans elle une puissance nulle en éclipse est lue comme une panne alors
   qu'elle est normale
4. la température — `telemetrie.temperature_c`, comparée aux seuils de
   `catalogue.seuils`, une dérive thermique précède souvent la perte de
   puissance
5. l'historique des interventions — `maintenance.date_debut` et `date_fin`,
   pour ne pas confondre une dégradation subie avec un arrêt planifié
6. les alarmes — `alarmes.severite` et `alarmes.type_alarme`, qui datent
   l'événement là où la télémétrie ne donne qu'une tendance

le périmètre d'analyse porte sur les 48 équipements instrumentés, les 8
onduleurs et les 8 radiateurs n'émettent ni télémétrie ni alarme, il s'agit
d'un choix d'instrumentation et non d'une perte de données

la formule `performance = puissance_reelle / puissance_attendue` ne vaut que
pour les équipements producteurs, un modèle de radiateur au catalogue a une
puissance nominale de 0 et rend donc cette division indéfinie


## points à vérifier avant toute transformation

**point 1 — la jointure vers le catalogue des modèles est rompue**

65 des 66 modèles référencés dans `equipements.csv`, tels que `MOD-PAN-754` ou
`MOD-BAT-107`, sont absents de `catalogue.modeles`, qui ne contient que 12 modèles à
numérotation ronde du type `MOD-PAN-100` ou `MOD-PAN-200`

*question* — s'agit-il de deux référentiels de générations différentes, ou d'un
identifiant tronqué

*impact* — la puissance nominale et le rendement sont inaccessibles, donc
`puissance_attendue` est incalculable et l'indicateur central du projet avec elle

une jointure dégradée par préfixe de famille, `MOD-PAN-` ou `MOD-BAT-`, est envisageable
mais perd en précision et devra être justifiée

**point 2 — EQ-006 a été ingéré deux fois**

`telemetrie.csv` compte 25 940 lignes pour EQ-006 contre environ 12 970 pour tous les
autres, soit exactement le double, et le même EQ-006 apparaît deux fois dans
`equipements.csv` en lignes strictement identiques

l'excédent de 12 970 lignes explique la quasi-totalité des 13 260 doublons de clé, les
290 restants correspondant aux 300 lignes exactement dupliquées

*question* — incident de rechargement d'un lot, ou double émission capteur

*impact* — il ne s'agit pas de 13 260 anomalies dispersées mais d'un incident unique,
et toute somme de production pour EQ-006 est actuellement doublée

**point 3 — lignes vides dans deux référentiels**

`sites.csv` compte 5 lignes pour 4 sites et `equipements.csv` 68 pour 66 équipements,
dans les deux cas toutes les colonnes présentent exactement un manquant, signature d'une
ligne ne contenant que des séparateurs

*question* — artefact d'export ou troncature

*impact* — une clé primaire nulle, non détectée par un simple test d'unicité, qui
générera une dimension fantôme dans le schéma en étoile

**point 4 — formats de dates hétérogènes et aucun fuseau horaire**


`telemetrie.timestamp` compte 635 337 valeurs ISO et 3 valeurs dans trois formats
distincts, et `equipements`, `maintenance` et `alarmes` contiennent chacun une date
déviante au format `jj/mm/aaaa`, `jj-mm-aaaa` ou `jj/mm/aaaa hhHmm`

surtout, aucun horodatage ne porte d'indication de fuseau

*question* — toutes les sources sont-elles bien en UTC

*impact* — le brief exige de l'UTC ISO 8601, en l'absence d'information il faudra poser
l'hypothèse explicitement, un décalage non détecté fausserait le rapprochement avec les
phases orbitales et donc l'ensemble des analyses de performance

le risque est confirmé, un premier essai de conversion a fait basculer deux mesures du
1er mai au 5 janvier par inversion du jour et du mois, sans produire la moindre erreur

**point 5 — clés étrangères invalides**

`equipements.site_id` contient `SITE-XXX` et `maintenance.equipement_id` contient
`EQ-XXX`, tous deux absents de leurs référentiels

*question* — marqueurs de saisie incomplète ou entités réellement inconnues

*impact* — ces lignes disparaîtront silencieusement des jointures, il faut décider avant
l'ETL entre le rejet documenté et le rattachement à un membre « inconnu » de la dimension

**point 6 — valeurs physiquement impossibles**

`telemetrie` monte jusqu'à 1 000 000 W et descend à −600 W, avec des températures de
999 °C et de −250 °C, invraisemblables pour un équipement alimenté

`orbite` donne un rayonnement de −200 à 5 000 W/m² alors que la constante solaire vaut
environ 1 368 W/m²

`equipements` porte une puissance nominale de −500 W et `maintenance` un coût de −250 €

*question* — 999 et 1 000 000 sont-ils des mesures ou des codes d'erreur capteur

*impact* — ce sont des manquants déguisés qu'aucun test `isna()` ne détecte, ils
contamineront toute moyenne tant qu'ils ne seront pas requalifiés

**point 7 — modalités hors référentiel**

`equipements.type` contient `inconnu`, `equipements.statut` et
`maintenance.type_intervention` contiennent `???`, `alarmes.type_alarme` contient
`UNKNOWN_TYPE` et `alarmes.severite` contient `URGENCE` là où les trois valeurs attendues
sont `info`, `warning` et `critical`

*question* — valeurs héritées d'un ancien système, ou saisies libres

*impact* — tout regroupement par type ou par sévérité produira des catégories parasites,
le cas `URGENCE` étant le plus sensible puisqu'il fausse le comptage des alarmes
critiques, qui sert de variable cible en partie 5

**point 8 — deux pièges de sémantique**

d'une part, une puissance nulle pendant une éclipse est un comportement normal, la
traiter comme une valeur aberrante reviendrait à supprimer près d'un tiers de la
télémétrie

d'autre part, `catalogue.modeles` contient un modèle de puissance nominale nulle,
cohérent pour un radiateur qui dissipe de la chaleur sans produire de courant, ce qui
rend `performance = réelle / attendue` indéfinie pour ces équipements

*impact* — la formule de performance ne s'applique qu'aux équipements producteurs, et la
distinction producteur ou non-producteur doit être portée par le modèle de données, pas
gérée au cas par cas dans les requêtes

## hypothèses à confirmer

**18 équipements sans aucune donnée**

les mêmes 18 équipements sont absents de `telemetrie.csv` et de `alarmes.json`, une
absence systématique et non aléatoire

leurs numéros, EQ-013 à EQ-016 puis EQ-029 à EQ-032, correspondent aux quatre derniers
équipements de chaque bloc de site

*hypothèse* — ces équipements appartiennent à un type non instrumenté

si elle est confirmée, il ne s'agit pas d'une perte de données mais d'un périmètre de
mesure à documenter, et les moyennes par site devront porter sur 48 équipements et non
sur 66

**[à vérifier — croiser ces 18 identifiants avec leur colonne `type`]**

**altitude de SITE-003**

manquante dans `sites.csv`, mais présente sous forme textuelle dans
`catalogue.references_sites.zone_orbitale` avec la valeur « LEO 420km », et la
correspondance est vérifiée sur les trois autres sites, 550 ↔ 550 km et 600 ↔ 600 km

récupérable par recoupement plutôt que par imputation

**inclinaison de SITE-004**

absente de toutes les sources, elle ne pourra être renseignée que par une hypothèse
physique assumée, une orbite héliosynchrone à 600 km ayant une inclinaison d'environ 97,8°