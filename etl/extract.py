import json
import sqlite3
import pandas as pd


def lire_csv(chemin, nrows=None):

    return pd.read_csv(chemin, dtype=str, nrows=nrows, encoding="utf-8")

def lire_json(chemin):

    with open(chemin, encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


def lire_sqlite(chemin):
    con = sqlite3.connect(chemin)
    try:
        noms = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table'", con
        )["name"]
        return {t: pd.read_sql(f"SELECT * FROM {t}", con) for t in noms}
    finally:
        con.close()


def lire_toutes_les_sources(dossier_raw, echantillon=None):

    sources = {
        "sites":       lire_csv(dossier_raw / "sites.csv"),
        "equipements": lire_csv(dossier_raw / "equipements.csv"),
        "maintenance": lire_csv(dossier_raw / "maintenance.csv"),
        "orbite":      lire_csv(dossier_raw / "orbite.csv"),
        "telemetrie":  lire_csv(dossier_raw / "telemetrie.csv", nrows=echantillon),
        "alarmes":     lire_json(dossier_raw / "alarmes.json"),
    }

    for nom_table, table in lire_sqlite(dossier_raw / "catalogue.db").items():
        sources[f"catalogue_{nom_table}"] = table

    return sources


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

    sources = lire_toutes_les_sources(config.RAW, echantillon=5000)

    for nom, df in sources.items():
        print(f"{nom:28s} {len(df):>8} lignes   {len(df.columns)} colonnes")