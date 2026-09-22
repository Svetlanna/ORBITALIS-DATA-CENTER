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



# 02 — chaîne ETL et qualité des données

## architecture retenue

trois zones séparées, chacune avec un rôle unique

| zone | contenu | format | écrite par |
|---|---|---|---|
| `data/raw` | les 7 sources livrées, jamais modifiées | csv, json, sqlite | personne |
| `data/cleaned` | une table par source, nettoyée et typée | csv | `run_etl.py` |
| `data/analytics` | la table d'analyse, jointe et enrichie | csv | `run_etl.py` |
| `data/rejets` | les lignes écartées avec leur motif | csv | `run_etl.py` |
| `data/quality` | les indicateurs et les neutralisations | csv | `run_etl.py` |

`raw` est en lecture seule, le nettoyage se fait en mémoire

le code est séparé selon la question à laquelle il répond

- `extract.py` lit, il ne juge rien
- `transform.py` répond à « que vaut cette valeur », un DataFrame entre, un DataFrame sort
- `quality.py` répond à « cette ligne a-t-elle le droit d'exister », il ne modifie aucune valeur
- `run_etl.py` orchestre et connaît seul les chemins
- `config.py` porte toute la règle, aucune constante métier n'est écrite dans le code

la chaîne entière se régénère par une commande, `python -m etl.run_etl`, en 15 secondes

## 1 — lecture et profilage

`exploration.py` profile les 7 sources sans rien transformer, il rend pour chacune le volume,
le type de chaque colonne, le taux de valeurs manquantes, les doublons de clé, les modalités
observées, les masques de formats de dates et l'intégrité référentielle

## 2 — harmonisation

**noms de colonnes** — `normaliser_colonnes` met tout en minuscules et remplace tout
caractère non alphanumérique par un souligné

**types** — `convertir_numeriques` force les colonnes de mesure, une valeur non convertible
devient NaN plutôt que de faire échouer la lecture

**dates** — toutes les colonnes temporelles sont converties en `datetime64` avec fuseau UTC

huit masques de formats distincts ont été observés dans les sources

| source | format dominant | formats exotiques |
|---|---|---|
| telemetrie | `%Y-%m-%dT%H:%M:%S` sur 635 337 lignes | 3, dont un avec fractions de seconde et suffixe Z |
| orbite | `%Y-%m-%d %H:%M:%S` sur 17 280 lignes | aucun |
| alarmes | `%Y-%m-%d %H:%M:%S` sur 520 lignes | 1, séparateur d'heure en lettre, `19h46` |
| maintenance | `%Y-%m-%d` sur 96 lignes | 1, `%d-%m-%Y` |
| equipements | `%Y-%m-%d` sur 66 lignes | 1, `%d/%m/%Y` |

`reparer_heures` normalise le `19h46` en `19:46` avant toute conversion

`convertir_dates` applique le format dominant exactement sur toute la série, puis un repli
sur la poignée de lignes restantes, la devinette ne porte donc jamais sur le gros du volume

**hypothèse documentée** — aucune source ne porte d'indication de fuseau, tous les horodatages
sont réputés être en UTC, cette convention est déclarée dans `config.FUSEAU` et non implicite

## 3 — valeurs manquantes et aberrantes

trois sorts possibles pour une donnée fautive, selon que l'identité de la ligne est atteinte

| sort | quand | effet |
|---|---|---|
| correction | format de date exotique | la valeur est lue correctement |
| neutralisation | valeur hors bornes physiques, modalité hors référentiel | la valeur devient NaN, **la ligne survit** |
| rejet | clé nulle ou dupliquée, clé étrangère invalide, intervalle incohérent | la ligne sort avec un motif |

le principe est qu'une valeur douteuse ne justifie pas de détruire les autres colonnes
de la même ligne, on ne rejette que si la ligne ne peut plus être identifiée ou rattachée

**230 valeurs neutralisées au total**, détaillées dans `data/quality/neutralisations.csv`

| source | colonne | valeurs neutralisées |
|---|---|---|
| telemetrie | temperature_c | 120 |
| telemetrie | puissance_w | 53 |
| orbite | phase | 30 |
| orbite | rayonnement_solaire_w_m2 | 20 |
| equipements | puissance_nominale_w, type, statut | 1 chacune |
| alarmes | severite, type_alarme | 1 chacune |
| maintenance | cout_eur, type_intervention | 1 chacune |

**une borne a dû être corrigée en cours de route** — la borne initiale sur `puissance_w`,
fixée à −100 W, neutralisait 37 655 valeurs, soit 5,9 % de la mesure principale

le croisement avec le type d'équipement a montré que ces 37 655 valeurs étaient
**toutes des batteries, sans exception**, une batterie en décharge produit une puissance
négative, ce qui est son fonctionnement normal et non une aberration

la borne a été portée à −700 W, le plancher réel observé étant −600 W, et le nombre de
neutralisations est tombé de 37 655 à 53, qui sont les vraies aberrations, dont 31 valeurs
à exactement 1 000 000 W

## 4 — doublons

13 262 lignes écartées pour clé dupliquée, dont 13 260 en télémétrie

la décomposition est exacte

12 960 EQ-006 ingéré deux fois, 12 960 x 2 = 25 920 lignes pour un seul équipement
300 lignes strictement identiques réparties sur les autres équipements
= 622 080 lignes acceptées




et 622 080 vaut exactement 48 équipements instrumentés x 12 960 horodatages,
soit 45 jours x 288 pas de 5 minutes

**après nettoyage, la télémétrie est exactement la grille théorique complète**, sans trou
ni excédent, ce qui confirme qu'aucune donnée n'a été perdue en amont et que tout
l'excédent brut était du doublon

la règle de conservation est `keep="first"`, la première occurrence rencontrée est gardée

## 5 — intégrité référentielle

les référentiels sont traités avant les tables qui les référencent, dans l'ordre
`sites`, `equipements`, `orbite`, `telemetrie`, `alarmes`, `maintenance`

une clé étrangère est donc vérifiée contre les lignes **acceptées** du parent, jamais
contre les lignes brutes, un équipement rejeté ne peut pas valider une mesure

deux ruptures réelles trouvées et rejetées

| source | valeur | cible manquante |
|---|---|---|
| equipements | `SITE-XXX` | `sites.site_id` |
| maintenance | `EQ-XXX` | `equipements.equipement_id` |

une clé étrangère **nulle** n'est pas traitée comme une clé étrangère invalide, la première
est une absence, la seconde est une erreur, ce choix est réglable par source avec
`fk_rejeter_nuls`, activé pour `maintenance` où une intervention sans équipement n'a aucun sens

## 6 — fichier des rejets

`data/rejets/rejets.csv`, 13 265 lignes, une par ligne écartée

chaque ligne conserve toutes ses colonnes d'origine plus trois colonnes de traçabilité

- `_source`, la table d'où elle vient
- `_ligne_source`, sa position dans le fichier brut, pour la retrouver
- `_motif_rejet`, un code issu de `config.py`, jamais du texte libre

**une ligne rejetée porte un seul motif**, le premier contrôle qui l'attrape, les contrôles
sont ordonnés de la cause vers le symptôme

cet ordre n'est pas cosmétique, il détermine ce que le rapport qualité annonce, une date
illisible rend la clé nulle, donc `DATE_ILLISIBLE` est testé avant `CLE_NULLE`, sinon le
rapport annoncerait zéro date illisible alors que c'est la vraie cause

les six motifs déclarés et les trois effectivement déclenchés

| motif | lignes |
|---|---|
| `CLE_DUPLIQUEE` | 13 262 |
| `FK_INVALIDE` | 2 |
| `INTERVALLE_INVALIDE` | 1 |
| `LIGNE_VIDE`, `CLE_NULLE`, `DATE_ILLISIBLE`, `DATE_HORS_PERIODE` | 0 |

le cas `INTERVALLE_INVALIDE` est MAINT-000, dont la date de fin, 2025-04-28, précède
sa date de début, 2025-05-01

## 7 — indicateurs de qualité

`data/quality/indicateurs_par_source.csv`

| source | lues | acceptées | rejetées | doublons |
|---|---|---|---|---|
| sites | 4 | 4 | 0 | 0 |
| equipements | 67 | 65 | 2 | 1 |
| orbite | 17 280 | 17 280 | 0 | 0 |
| telemetrie | 635 340 | 622 080 | 13 260 | 13 260 |
| alarmes | 521 | 520 | 1 | 1 |
| maintenance | 97 | 95 | 2 | 0 |
| catalogue_modeles | 12 | 12 | 0 | 0 |
| catalogue_seuils_alarmes | 6 | 6 | 0 | 0 |
| catalogue_references_sites | 4 | 4 | 0 | 0 |
| **total** | **653 331** | **640 066** | **13 265** | **13 262** |

l'équation `lues = acceptées + rejetées` est vérifiée par un `assert` à chaque appel,
une perte de ligne arrête la chaîne à l'endroit exact du problème au lieu de produire
un chiffre faux trois étapes plus loin

## point critique — distinguer l'éclipse de l'anomalie

une puissance nulle en éclipse est normale, la confondre avec une panne fausserait
toute la partie prédictive

la télémétrie est au pas de 5 minutes par équipement, le contexte orbital au pas de
15 minutes par site, et aucune colonne n'est commune aux deux tables

`joindre_contexte_orbital` construit le pont en deux temps

1. `telemetrie` vers `equipements` pour obtenir le `site_id`
2. calage de l'horodatage sur la grille de 15 minutes avec `floor`, puis jointure sur
   le couple créneau et site pour obtenir la `phase`

le calage utilise `floor` et non `round`, un contexte orbital est valide **à partir** de
son horodatage, une mesure de 00h07 appartient donc au créneau de 00h00 et non à celui
de 00h15 qui n'avait pas encore commencé

deux protections encadrent la jointure

`drop_duplicates` sur la clé de droite, sans lequel les 25 940 mesures d'EQ-006, dupliqué
dans `equipements`, auraient été doublées à leur tour, ce qui aurait ajouté 25 940 lignes
silencieusement

un `assert` sur le nombre de lignes, une jointure à gauche ne doit jamais changer le
cardinal de la table de gauche

**résultat du rattachement**

| phase | lignes | puissance médiane |
|---|---|---|
| ensoleillement | 388 044 | 747,21 W |
| eclipse | 232 956 | 0,00 W |
| indetermine | 1 080 | — |

taux de rattachement de 99,83 %, et l'écart entre 0 W et 747 W confirme que le signal
orbital est net

**les 1 080 lignes indéterminées** proviennent des 30 créneaux orbitaux dont la `phase`
valait `inconnu` dans la source

ces lignes reçoivent un troisième état explicite, `indetermine`, plutôt que NaN, parce
qu'un test `phase == "eclipse"` sur une valeur manquante rend faux et ferait basculer
ces mesures du côté « hors éclipse », donc du côté jugé anormal, une donnée qu'on ne
sait pas qualifier n'est pas une donnée normale

## zone analytics

`data/analytics/mesures_enrichies.csv`, 622 080 lignes et 20 colonnes

la table joint chaque mesure à son équipement, son site et son contexte orbital, puis
ajoute quatre colonnes calculées

| colonne | formule |
|---|---|
| `puissance_attendue_w` | `puissance_nominale_w` x `rayonnement` |
| `performance` | `puissance_w` / `puissance_attendue_w` |
| `ecart_w` | `puissance_w` moins `puissance_attendue_w` |
| `hors_eclipse` | vrai si la phase vaut `ensoleillement` |

**la formule ne s'applique qu'aux producteurs**, c'est-à-dire aux panneaux solaires

la mesure de la puissance médiane en éclipse par type le justifie

| type | médiane en éclipse |
|---|---|
| panneau_solaire | 0,00 W |
| batterie | 249,14 W |
| convertisseur_DC | 125,73 W |

seul le panneau suit le soleil, une batterie continue de débiter en éclipse puisqu'elle
se décharge, un convertisseur convertit ce qui lui arrive, appliquer la formule à l'un
d'eux donnerait une performance infinie là où le rayonnement est nul

le contrôle de cohérence de la formule est le ratio médian `reelle / (nominale x rayonnement)`
mesuré à 1,068 sur les panneaux au soleil, une valeur proche de 1 confirme la définition

la performance est donc calculable sur 274 388 mesures sur 622 080, les autres
correspondent aux non-producteurs, aux phases d'éclipse et aux rayonnements nuls

## limites connues

**la jointure catalogue reste rompue**, 65 des 66 modèles de `equipements.csv` sont
absents de `catalogue.modeles`, la famille de préfixes ne suffit pas à les rapprocher
puisque quatre modèles de panneaux coexistent avec des puissances nominales différentes

le blocage a été contourné et non résolu, `equipements.csv` porte sa propre colonne
`puissance_nominale_w`, renseignée pour les 65 équipements acceptés, c'est elle qui sert
de référence pour `puissance_attendue_w`

**les bornes de plausibilité dépendent de la source et non du type d'équipement**, un
panneau solaire à −400 W serait une vraie anomalie alors qu'une batterie à −400 W est
normale, la borne actuelle est donc calibrée sur le cas le plus permissif

**un type d'alarme sur six n'a aucun seuil** dans `catalogue.seuils_alarmes`, ni
`seuil_warning`, ni `seuil_critical`, ni `unite`

**437 alarmes sur 521 ont un message qui nomme un type différent de leur `type_alarme`**,
aucune des deux colonnes n'a été déclarée prioritaire à ce stade

**`config.py` porte un nom qui entre en collision avec un paquet public du même nom**,
ce qui a provoqué des imports fantômes, le fichier gagnerait à s'appeler `parametres.py`


