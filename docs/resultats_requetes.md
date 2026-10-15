# Resultats des requetes ORBITALIS

- base : `data\db\orbitalis_etoile.db`
- fichier : `sql\analyse.sql`
- genere le 2026-10-15 13:55

## Query1 production totale par equipement et par jour (kWh)

```sql
-- seuls les producteurs (panneaux solaires) produisent, les batteries
-- et convertisseurs transferent de l'energie
SELECT e.equipement_id,
       t.date,
       ROUND(SUM(f.energie_wh) / 1000.0, 3) AS production_kwh,
       COUNT(f.energie_wh)                  AS nb_mesures
FROM fait_mesure f
JOIN dim_equipement e ON e.id_equipement = f.id_equipement
JOIN dim_temps      t ON t.id_temps      = f.id_temps
WHERE e.est_producteur = 1
GROUP BY e.equipement_id, t.date
ORDER BY e.equipement_id, t.date;
```

**1080 ligne(s)** - 0.35 s

| equipement_id | date | production_kwh | nb_mesures |
| --- | --- | --- | --- |
| EQ-001 | 2025-05-01 | 5.992 | 281 |
| EQ-001 | 2025-05-02 | 5.82 | 280 |
| EQ-001 | 2025-05-03 | 5.895 | 281 |
| EQ-001 | 2025-05-04 | 5.751 | 277 |
| EQ-001 | 2025-05-05 | 5.888 | 284 |
| EQ-001 | 2025-05-06 | 5.784 | 286 |
| EQ-001 | 2025-05-07 | 5.102 | 276 |
| EQ-001 | 2025-05-08 | 5.488 | 274 |
| EQ-001 | 2025-05-09 | 5.461 | 281 |
| EQ-001 | 2025-05-10 | 5.416 | 276 |
| EQ-001 | 2025-05-11 | 5.288 | 279 |
| EQ-001 | 2025-05-12 | 5.284 | 279 |
| EQ-001 | 2025-05-13 | 4.821 | 285 |
| EQ-001 | 2025-05-14 | 5.257 | 285 |
| EQ-001 | 2025-05-15 | 5.052 | 278 |
| EQ-001 | 2025-05-16 | 5.112 | 279 |
| EQ-001 | 2025-05-17 | 4.95 | 281 |
| EQ-001 | 2025-05-18 | 4.894 | 277 |
| EQ-001 | 2025-05-19 | 4.977 | 283 |
| EQ-001 | 2025-05-20 | 4.78 | 280 |
| EQ-001 | 2025-05-21 | 4.659 | 278 |
| EQ-001 | 2025-05-22 | 4.669 | 278 |
| EQ-001 | 2025-05-23 | 4.686 | 280 |
| EQ-001 | 2025-05-24 | 4.661 | 279 |
| EQ-001 | 2025-05-25 | 4.577 | 279 |
| EQ-001 | 2025-05-26 | 4.526 | 283 |
| EQ-001 | 2025-05-27 | 3.987 | 277 |
| EQ-001 | 2025-05-28 | 4.359 | 280 |
| EQ-001 | 2025-05-29 | 4.222 | 279 |
| EQ-001 | 2025-05-30 | 4.23 | 283 |

_... 30 premieres lignes affichees sur 1080._

## Query2 equipements aux performances moyennes les plus faibles, hors eclipse

```sql
SELECT e.equipement_id,
       e.type_equipement,
       s.nom                         AS site,
       ROUND(AVG(f.performance), 4)  AS performance_moyenne,
       COUNT(f.performance)          AS nb_mesures
FROM fait_mesure f
JOIN dim_phase      p ON p.id_phase      = f.id_phase
JOIN dim_equipement e ON e.id_equipement = f.id_equipement
JOIN dim_site       s ON s.id_site       = e.id_site
WHERE p.phase = 'ensoleillement'
  AND f.performance IS NOT NULL
GROUP BY e.equipement_id, e.type_equipement, s.nom
HAVING COUNT(f.performance) >= 100          -- une moyenne sur 3 mesures ne veut rien dire
ORDER BY performance_moyenne ASC
LIMIT 10;
```

**10 ligne(s)** - 0.30 s

| equipement_id | type_equipement | site | performance_moyenne | nb_mesures |
| --- | --- | --- | --- | --- |
| EQ-035 | panneau_solaire | ORBITALIS-Gamma | 0.3779 | 7858 |
| EQ-006 | panneau_solaire | ORBITALIS-Alpha | 0.4415 | 7904 |
| EQ-001 | panneau_solaire | ORBITALIS-Alpha | 0.6132 | 7875 |
| EQ-019 | panneau_solaire | ORBITALIS-Beta | 0.6559 | 7878 |
| EQ-017 | panneau_solaire | ORBITALIS-Beta | 0.667 | 7897 |
| EQ-038 | panneau_solaire | ORBITALIS-Gamma | 0.7616 | 7874 |
| EQ-002 | panneau_solaire | ORBITALIS-Alpha | 0.7919 | 7894 |
| EQ-034 | panneau_solaire | ORBITALIS-Gamma | 0.9015 | 7846 |
| EQ-052 | panneau_solaire | ORBITALIS-Delta | 0.9254 | 7888 |
| EQ-003 | panneau_solaire | ORBITALIS-Alpha | 0.9746 | 7876 |

## Query3 nombre d'alarmes par equipement et par severite

```sql
-- LEFT JOIN depuis la dimension pour voir aussi les equipements a 0 alarme
SELECT e.equipement_id,
       SUM(CASE WHEN a.severite = 'info'     THEN 1 ELSE 0 END) AS info,
       SUM(CASE WHEN a.severite = 'warning'  THEN 1 ELSE 0 END) AS warning,
       SUM(CASE WHEN a.severite = 'critical' THEN 1 ELSE 0 END) AS critical,
       SUM(CASE WHEN a.alarme_id IS NOT NULL AND a.severite IS NULL
                THEN 1 ELSE 0 END)                              AS non_renseignee,
       COUNT(a.alarme_id)                                       AS total
FROM dim_equipement e
LEFT JOIN fait_alarme a ON a.id_equipement = e.id_equipement
GROUP BY e.equipement_id
ORDER BY total DESC, critical DESC;
```

**64 ligne(s)** - 0.00 s

| equipement_id | info | warning | critical | non_renseignee | total |
| --- | --- | --- | --- | --- | --- |
| EQ-022 | 5 | 7 | 7 | 0 | 19 |
| EQ-021 | 3 | 13 | 3 | 0 | 19 |
| EQ-055 | 2 | 11 | 4 | 0 | 17 |
| EQ-011 | 3 | 4 | 9 | 0 | 16 |
| EQ-006 | 3 | 5 | 8 | 0 | 16 |
| EQ-053 | 2 | 4 | 9 | 0 | 15 |
| EQ-018 | 3 | 4 | 7 | 0 | 14 |
| EQ-041 | 3 | 4 | 7 | 0 | 14 |
| EQ-042 | 5 | 3 | 6 | 0 | 14 |
| EQ-033 | 3 | 4 | 6 | 0 | 13 |
| EQ-057 | 1 | 7 | 5 | 0 | 13 |
| EQ-054 | 2 | 8 | 3 | 0 | 13 |
| EQ-020 | 3 | 8 | 2 | 0 | 13 |
| EQ-001 | 3 | 3 | 6 | 0 | 12 |
| EQ-017 | 1 | 6 | 4 | 1 | 12 |
| EQ-005 | 4 | 5 | 3 | 0 | 12 |
| EQ-010 | 2 | 8 | 2 | 0 | 12 |
| EQ-004 | 1 | 5 | 5 | 0 | 11 |
| EQ-028 | 1 | 6 | 4 | 0 | 11 |
| EQ-035 | 2 | 5 | 4 | 0 | 11 |
| EQ-039 | 3 | 4 | 4 | 0 | 11 |
| EQ-040 | 2 | 6 | 3 | 0 | 11 |
| EQ-050 | 4 | 5 | 2 | 0 | 11 |
| EQ-051 | 1 | 2 | 7 | 0 | 10 |
| EQ-019 | 0 | 4 | 6 | 0 | 10 |
| EQ-026 | 2 | 2 | 6 | 0 | 10 |
| EQ-024 | 1 | 4 | 5 | 0 | 10 |
| EQ-034 | 1 | 4 | 5 | 0 | 10 |
| EQ-037 | 1 | 4 | 5 | 0 | 10 |
| EQ-056 | 1 | 5 | 4 | 0 | 10 |

_... 30 premieres lignes affichees sur 64._

## Query4 delai moyen entre deux maintenances d'un meme equipement (jours)

```sql
WITH maintenances AS (
    SELECT e.equipement_id,
           td.timestamp AS debut,
           LAG(td.timestamp) OVER (PARTITION BY e.equipement_id
                                   ORDER BY td.timestamp) AS debut_precedent
    FROM fait_maintenance m
    JOIN dim_equipement e  ON e.id_equipement = m.id_equipement
    JOIN dim_temps      td ON td.id_temps     = m.id_temps_debut
)
SELECT equipement_id,
       COUNT(*) + 1                                                  AS nb_maintenances,
       ROUND(AVG(julianday(debut) - julianday(debut_precedent)), 1) AS delai_moyen_jours
FROM maintenances
WHERE debut_precedent IS NOT NULL       -- la 1re maintenance n'a pas de precedente
GROUP BY equipement_id
ORDER BY delai_moyen_jours;
```

**31 ligne(s)** - 0.01 s

| equipement_id | nb_maintenances | delai_moyen_jours |
| --- | --- | --- |
| EQ-020 | 2 | 2.0 |
| EQ-025 | 2 | 2.0 |
| EQ-043 | 2 | 2.0 |
| EQ-057 | 2 | 4.0 |
| EQ-006 | 5 | 4.3 |
| EQ-001 | 2 | 5.0 |
| EQ-039 | 3 | 5.0 |
| EQ-055 | 2 | 5.0 |
| EQ-028 | 3 | 5.5 |
| EQ-049 | 2 | 6.0 |
| EQ-051 | 4 | 6.7 |
| EQ-022 | 3 | 7.5 |
| EQ-052 | 2 | 8.0 |
| EQ-005 | 4 | 8.7 |
| EQ-011 | 3 | 9.5 |
| EQ-034 | 3 | 9.5 |
| EQ-033 | 2 | 10.0 |
| EQ-021 | 4 | 11.0 |
| EQ-036 | 4 | 12.3 |
| EQ-044 | 3 | 12.5 |
| EQ-024 | 3 | 13.5 |
| EQ-035 | 3 | 16.0 |
| EQ-040 | 3 | 16.0 |
| EQ-008 | 3 | 16.5 |
| EQ-053 | 2 | 20.0 |
| EQ-017 | 2 | 21.0 |
| EQ-019 | 2 | 22.0 |
| EQ-002 | 2 | 23.0 |
| EQ-027 | 2 | 26.0 |
| EQ-056 | 2 | 31.0 |

_... 30 premieres lignes affichees sur 31._

## Query4bis meme delai, tous equipements confondus

```sql
WITH maintenances AS (
    SELECT m.id_equipement,
           td.timestamp AS debut,
           LAG(td.timestamp) OVER (PARTITION BY m.id_equipement
                                   ORDER BY td.timestamp) AS debut_precedent
    FROM fait_maintenance m
    JOIN dim_temps td ON td.id_temps = m.id_temps_debut
)
SELECT ROUND(AVG(julianday(debut) - julianday(debut_precedent)), 1) AS delai_moyen_jours,
       COUNT(debut_precedent)                                       AS nb_intervalles
FROM maintenances;
```

**1 ligne(s)** - 0.01 s

| delai_moyen_jours | nb_intervalles |
| --- | --- |
| 11.1 | 52 |

## Query5 equipements non maintenus depuis plus de 90 jours

```sql
-- date de reference = derniere mesure disponible (pas la date du jour,
-- sinon tout serait "en retard" puisque les donnees datent de 2025)
-- jamais maintenu -> on compte depuis la date d'installation
WITH reference AS (
    SELECT MAX(t.timestamp) AS date_ref
    FROM fait_mesure f JOIN dim_temps t ON t.id_temps = f.id_temps
),
derniere AS (
    SELECT m.id_equipement, MAX(tf.timestamp) AS derniere_maintenance
    FROM fait_maintenance m
    JOIN dim_temps tf ON tf.id_temps = m.id_temps_fin
    GROUP BY m.id_equipement
)
SELECT e.equipement_id,
       e.type_equipement,
       e.date_installation,
       d.derniere_maintenance,
       CAST(julianday(r.date_ref)
            - julianday(COALESCE(d.derniere_maintenance, e.date_installation)) AS INTEGER)
                                                     AS jours_sans_maintenance
FROM dim_equipement e
CROSS JOIN reference r
LEFT JOIN derniere d ON d.id_equipement = e.id_equipement
WHERE julianday(r.date_ref)
      - julianday(COALESCE(d.derniere_maintenance, e.date_installation)) > 90
ORDER BY jours_sans_maintenance DESC;
```

**20 ligne(s)** - 0.12 s

| equipement_id | type_equipement | date_installation | derniere_maintenance | jours_sans_maintenance |
| --- | --- | --- | --- | --- |
| EQ-047 | radiateur | 2024-03-15 |  | 456 |
| EQ-048 | radiateur | 2024-03-24 |  | 447 |
| EQ-061 | onduleur | 2024-03-31 |  | 440 |
| EQ-013 | onduleur | 2024-04-06 |  | 434 |
| EQ-018 | panneau_solaire | 2024-04-24 |  | 416 |
| EQ-050 | panneau_solaire | 2024-04-24 |  | 416 |
| EQ-041 | convertisseur_DC | 2024-05-11 |  | 399 |
| EQ-030 | onduleur | 2024-05-25 |  | 385 |
| EQ-063 | radiateur | 2024-07-02 |  | 347 |
| EQ-062 | onduleur | 2024-07-14 |  | 335 |
| EQ-012 | batterie | 2024-09-14 |  | 273 |
| EQ-014 | onduleur | 2024-09-24 |  | 263 |
| EQ-029 | onduleur | 2024-10-03 |  | 254 |
| EQ-032 | radiateur | 2024-10-20 |  | 237 |
| EQ-031 | radiateur | 2024-12-15 |  | 181 |
| EQ-003 | panneau_solaire | 2024-12-19 |  | 177 |
| EQ-016 | radiateur | 2025-01-04 |  | 161 |
| EQ-064 | radiateur | 2025-01-04 |  | 161 |
| EQ-045 | onduleur | 2025-01-20 |  | 145 |
| EQ-015 | radiateur | 2025-01-30 |  | 135 |

## Query6 perte de production estimee par site (kWh)

```sql
-- seulement en ensoleillement : en eclipse rien n'est attendu, donc rien n'est perdu
-- perte_wh < 0 = surproduction, on ne la laisse pas compenser les pertes
SELECT s.nom                                                         AS site,
       ROUND(SUM(CASE WHEN f.perte_wh > 0 THEN f.perte_wh END) / 1000.0, 2) AS perte_kwh,
       ROUND(SUM(f.energie_attendue_wh) / 1000.0, 2)                 AS attendu_kwh,
       ROUND(100.0 * SUM(CASE WHEN f.perte_wh > 0 THEN f.perte_wh END)
             / SUM(f.energie_attendue_wh), 1)                       AS perte_pct
FROM fait_mesure f
JOIN dim_site  s ON s.id_site  = f.id_site
JOIN dim_phase p ON p.id_phase = f.id_phase
WHERE p.production_attendue = 1
  AND f.energie_attendue_wh IS NOT NULL
GROUP BY s.nom
ORDER BY perte_kwh DESC;
```

**4 ligne(s)** - 0.31 s

| site | perte_kwh | attendu_kwh | perte_pct |
| --- | --- | --- | --- |
| ORBITALIS-Gamma | 1106.65 | 4268.35 | 25.9 |
| ORBITALIS-Alpha | 801.14 | 3146.03 | 25.5 |
| ORBITALIS-Beta | 532.53 | 3700.37 | 14.4 |
| ORBITALIS-Delta | 251.62 | 3894.75 | 6.5 |

## Query7 evolution de la performance d'un equipement dans le temps (fonctions de fenetre)

```sql
-- 1) performance moyenne par jour   2) moyenne glissante sur 7 jours
-- 3) variation par rapport a la veille (LAG)   4) rang du jour (RANK)
WITH quotidien AS (
    SELECT t.date,
           AVG(f.performance) AS perf_jour
    FROM fait_mesure f
    JOIN dim_equipement e ON e.id_equipement = f.id_equipement
    JOIN dim_temps      t ON t.id_temps      = f.id_temps
    WHERE e.equipement_id = 'EQ-001'
      AND f.performance IS NOT NULL
    GROUP BY t.date
)
SELECT date,
       ROUND(perf_jour, 4) AS perf_jour,
       ROUND(AVG(perf_jour) OVER (ORDER BY date
                                  ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 4) AS moyenne_7j,
       ROUND(perf_jour - LAG(perf_jour) OVER (ORDER BY date), 4)               AS variation_veille,
       RANK() OVER (ORDER BY perf_jour)                                         AS rang_du_pire
FROM quotidien
ORDER BY date;
```

**45 ligne(s)** - 0.16 s

| date | perf_jour | moyenne_7j | variation_veille | rang_du_pire |
| --- | --- | --- | --- | --- |
| 2025-05-01 | 0.5421 | 0.5421 |  | 43 |
| 2025-05-02 | 0.5164 | 0.5292 | -0.0257 | 39 |
| 2025-05-03 | 0.5297 | 0.5294 | 0.0133 | 41 |
| 2025-05-04 | 0.6708 | 0.5648 | 0.1411 | 45 |
| 2025-05-05 | 0.5472 | 0.5612 | -0.1236 | 44 |
| 2025-05-06 | 0.5191 | 0.5542 | -0.0281 | 40 |
| 2025-05-07 | 0.4709 | 0.5423 | -0.0482 | 33 |
| 2025-05-08 | 0.5298 | 0.5406 | 0.0589 | 42 |
| 2025-05-09 | 0.4948 | 0.5375 | -0.0349 | 38 |
| 2025-05-10 | 0.4931 | 0.5323 | -0.0017 | 37 |
| 2025-05-11 | 0.4695 | 0.5035 | -0.0236 | 32 |
| 2025-05-12 | 0.4894 | 0.4952 | 0.0199 | 36 |
| 2025-05-13 | 0.4234 | 0.4816 | -0.066 | 23 |
| 2025-05-14 | 0.4734 | 0.4819 | 0.05 | 34 |
| 2025-05-15 | 0.4859 | 0.4757 | 0.0124 | 35 |
| 2025-05-16 | 0.4594 | 0.4706 | -0.0265 | 30 |
| 2025-05-17 | 0.4484 | 0.4642 | -0.0109 | 28 |
| 2025-05-18 | 0.4611 | 0.463 | 0.0126 | 31 |
| 2025-05-19 | 0.4505 | 0.4574 | -0.0106 | 29 |
| 2025-05-20 | 0.4429 | 0.4602 | -0.0076 | 27 |
| 2025-05-21 | 0.4241 | 0.4532 | -0.0188 | 24 |
| 2025-05-22 | 0.4381 | 0.4463 | 0.014 | 26 |
| 2025-05-23 | 0.4243 | 0.4413 | -0.0138 | 25 |
| 2025-05-24 | 0.4145 | 0.4365 | -0.0098 | 20 |
| 2025-05-25 | 0.4145 | 0.4298 | 0.0 | 21 |
| 2025-05-26 | 0.4196 | 0.4254 | 0.0051 | 22 |
| 2025-05-27 | 0.365 | 0.4143 | -0.0547 | 13 |
| 2025-05-28 | 0.4052 | 0.4116 | 0.0403 | 19 |
| 2025-05-29 | 0.3964 | 0.4057 | -0.0088 | 18 |
| 2025-05-30 | 0.3853 | 0.4001 | -0.0111 | 17 |

_... 30 premieres lignes affichees sur 45._

## Query8 ensoleillement vs eclipse, sans traiter l'eclipse comme une panne

```sql
-- on compare ce qui est comparable : production, rayonnement, temperature
-- la performance n'est jugee que la ou une production est attendue
-- une "sous-performance" n'est comptee qu'en ensoleillement
SELECT e.type_equipement,
       p.phase,
       COUNT(*)                                       AS nb_mesures,
       ROUND(AVG(f.rayonnement), 3)                   AS rayonnement_moyen,
       ROUND(AVG(f.puissance_w), 1)                   AS puissance_moyenne_w,
       ROUND(SUM(f.energie_wh) / 1000.0, 1)           AS energie_kwh,
       ROUND(AVG(f.temperature_c), 1)                 AS temperature_moyenne_c,
       CASE WHEN p.production_attendue = 1
            THEN ROUND(AVG(f.performance), 4) END     AS performance_moyenne,
       -- ponderee : sum(reel) / sum(attendu), insensible aux tout petits denominateurs
       CASE WHEN p.production_attendue = 1
            THEN ROUND(SUM(CASE WHEN f.energie_attendue_wh IS NOT NULL THEN f.energie_wh END)
                       / SUM(f.energie_attendue_wh), 4) END AS performance_ponderee,
       CASE WHEN p.production_attendue = 1
            THEN SUM(CASE WHEN f.performance < 0.8 THEN 1 ELSE 0 END) END
                                                      AS mesures_sous_80pct
FROM fait_mesure f
JOIN dim_phase      p ON p.id_phase      = f.id_phase
JOIN dim_equipement e ON e.id_equipement = f.id_equipement
GROUP BY e.type_equipement, p.phase
ORDER BY e.type_equipement, p.phase;
```

**9 ligne(s)** - 1.37 s

| type_equipement | phase | nb_mesures | rayonnement_moyen | puissance_moyenne_w | energie_kwh | temperature_moyenne_c | performance_moyenne | performance_ponderee | mesures_sous_80pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| batterie | eclipse | 58239 | 0.098 | 269.1 | 1273.1 | -35.0 |  |  |  |
| batterie | ensoleillement | 97011 | 0.55 | 267.4 | 2107.1 | 38.0 |  |  | 0 |
| batterie | indetermine | 270 | 0.41 | 256.6 | 5.7 | 16.6 |  |  |  |
| convertisseur_DC | eclipse | 58239 | 0.098 | 142.2 | 672.3 | -35.0 |  |  |  |
| convertisseur_DC | ensoleillement | 97011 | 0.55 | 1196.7 | 9435.5 | 38.0 |  |  | 0 |
| convertisseur_DC | indetermine | 270 | 0.419 | 822.3 | 17.7 | 16.3 |  |  |  |
| panneau_solaire | eclipse | 116478 | 0.098 | -0.0 | -0.1 | -35.0 |  |  |  |
| panneau_solaire | ensoleillement | 194022 | 0.55 | 934.6 | 14738.7 | 38.0 | 0.9985 | 0.982 | 72510 |
| panneau_solaire | indetermine | 540 | 0.419 | 630.1 | 27.7 | 16.0 |  |  |  |

## Query9 cout estime des pertes de production non anticipees

```sql
-- non anticipee = perte en ensoleillement (l'eclipse est prevue)
--                 hors periode de maintenance (l'arret est planifie)
-- hypothese de prix a documenter : 0.15 EUR / kWh (parametre a ajuster)
WITH parametres AS (SELECT 0.15 AS prix_eur_kwh),
pertes AS MATERIALIZED (
    SELECT f.id_site, f.perte_wh
    FROM fait_mesure f
    JOIN dim_phase p ON p.id_phase = f.id_phase
    JOIN dim_temps t ON t.id_temps = f.id_temps
    WHERE p.production_attendue = 1
      AND f.perte_wh > 0
      AND NOT EXISTS (
          SELECT 1
          FROM fait_maintenance m
          JOIN dim_temps td ON td.id_temps = m.id_temps_debut
          JOIN dim_temps tf ON tf.id_temps = m.id_temps_fin
          WHERE m.id_equipement = f.id_equipement
            AND t.timestamp >= td.timestamp
            AND t.timestamp <  tf.timestamp
      )
)
SELECT s.nom                                              AS site,
       ROUND(SUM(pe.perte_wh) / 1000.0, 2)                   AS perte_non_anticipee_kwh,
       ROUND(SUM(pe.perte_wh) / 1000.0 * pa.prix_eur_kwh, 2) AS cout_eur
FROM pertes pe
JOIN dim_site s ON s.id_site = pe.id_site
CROSS JOIN parametres pa
GROUP BY s.nom
UNION ALL
SELECT 'TOTAL',
       ROUND(SUM(pe.perte_wh) / 1000.0, 2),
       ROUND(SUM(pe.perte_wh) / 1000.0 * (SELECT prix_eur_kwh FROM parametres), 2)
FROM pertes pe;
```

**5 ligne(s)** - 0.54 s

| site | perte_non_anticipee_kwh | cout_eur |
| --- | --- | --- |
| ORBITALIS-Alpha | 678.07 | 101.71 |
| ORBITALIS-Beta | 472.5 | 70.87 |
| ORBITALIS-Delta | 215.74 | 32.36 |
| ORBITALIS-Gamma | 914.87 | 137.23 |
| TOTAL | 2281.18 | 342.18 |
