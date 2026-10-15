
-- requetes d'analyse sur le modele en etoile (SQLite)
-- data/db/orbitalis_etoile.db
-- energie_wh = puissance_w x 5/60 h pas de telemetrie de 5 minutes
-- ============================================================


-- @Query1 production totale par equipement et par jour (kWh)
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


-- @Query2 equipements aux performances moyennes les plus faibles, hors eclipse
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


-- @Query3 nombre d'alarmes par equipement et par severite
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


-- @Query4 delai moyen entre deux maintenances d'un meme equipement (jours)
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


-- @Query4bis meme delai, tous equipements confondus
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


-- @Query5 equipements non maintenus depuis plus de 90 jours
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


-- @Query6 perte de production estimee par site (kWh)
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


-- @Query7 evolution de la performance d'un equipement dans le temps (fonctions de fenetre)
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


-- @Query8 ensoleillement vs eclipse, sans traiter l'eclipse comme une panne
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


-- @Query9 cout estime des pertes de production non anticipees
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