import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C

DOSSIER_DB    = C.RACINE / "data" / "db"
NOM_CONCEPTUEL = "orbitalis_conceptuel.db"
NOM_ETOILE     = "orbitalis_etoile.db"

# une ligne = 1 panneau x 1 jour, uniquement au soleil
# (en eclipse un panneau ne produit rien, ce n'est pas de la degradation)
REQUETE_PRODUCTION = """
SELECT e.equipement_id,
       s.nom                              AS site,
       e.modele_code                      AS modele,
       e.puissance_nominale_w,
       t.date,
       SUM(f.energie_wh) / 1000.0         AS energie_kwh,
       AVG(f.puissance_w)                 AS puissance_moyenne_w,
       AVG(f.temperature_c)               AS temperature_moyenne_c,
       COUNT(f.puissance_w)               AS nb_mesures
FROM fait_mesure f
JOIN dim_equipement e ON e.id_equipement = f.id_equipement
JOIN dim_site       s ON s.id_site       = e.id_site
JOIN dim_phase      p ON p.id_phase      = f.id_phase
JOIN dim_temps      t ON t.id_temps      = f.id_temps
WHERE e.est_producteur = 1
  AND p.phase = 'ensoleillement'
GROUP BY e.equipement_id, s.nom, e.modele_code, e.puissance_nominale_w, t.date
ORDER BY e.equipement_id, t.date
"""

# une ligne = 1 equipement x 1 jour ou il y a eu au moins une alarme
REQUETE_ALARMES = """
SELECT e.equipement_id,
       t.date,
       COUNT(*)            AS nb_alarmes,
       SUM(a.est_critique) AS nb_alarmes_critiques
FROM fait_alarme a
JOIN dim_equipement e ON e.id_equipement = a.id_equipement
JOIN dim_temps      t ON t.id_temps      = a.id_temps
GROUP BY e.equipement_id, t.date
"""


def lire_donnees(chemin_db=DOSSIER_DB / NOM_ETOILE):
    if not chemin_db.exists():
        raise SystemExit(f"base introuvable : {chemin_db}\nlancez d'abord python etl/load.py")

    with sqlite3.connect(chemin_db) as con:
        production = pd.read_sql_query(REQUETE_PRODUCTION, con, parse_dates=["date"])
        alarmes = pd.read_sql_query(REQUETE_ALARMES, con, parse_dates=["date"])

    # un jour sans alarme n'existe pas dans "alarmes" -> le LEFT merge met NaN -> on remplace par 0
    df = production.merge(alarmes, on=["equipement_id", "date"], how="left")
    df[["nb_alarmes", "nb_alarmes_critiques"]] = (
        df[["nb_alarmes", "nb_alarmes_critiques"]].fillna(0).astype(int))
    return df


if __name__ == "__main__":
    df = lire_donnees()
    print(df.head(10).to_string(index=False))
    print(f"\n{len(df)} lignes, {df['equipement_id'].nunique()} panneaux, "
          f"{df['date'].nunique()} jours")
    print(df.dtypes)