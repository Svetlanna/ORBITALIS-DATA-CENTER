
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C

DOSSIER_DB     = C.RACINE / "data" / "db"
NOM_CONCEPTUEL = "orbitalis_conceptuel.db"

FENETRE = pd.Timedelta("24h")

FEATURES = [
    # mesures actuelles (au soleil uniquement)
    "puissance_w",
    "rayonnement",
    "temperature_c",
    "tension_v",
    "courant_a",
    # le panneau
    "puissance_nominale_w",
    "age_jours",
    # l'historique
    "puissance_moyenne_24h",
    "tendance_24h",
    "alarmes_24h",
    "heures_depuis_maintenance",
]


#  lecture : une requete par table

REQUETE_EQUIPEMENTS = """
SELECT equipement_id,
       site_id,
       type_equipement,
       puissance_nominale_w,
       date_installation
FROM equipement
WHERE type_equipement = 'panneau_solaire'
"""

REQUETE_MESURES = """
SELECT m.horodatage,
       m.equipement_id,
       m.puissance_w,
       m.rayonnement,
       m.temperature_c,
       m.tension_v,
       m.courant_a
FROM mesure m
JOIN equipement e ON e.equipement_id = m.equipement_id
WHERE e.type_equipement = 'panneau_solaire'
"""

REQUETE_ORBITE = """
SELECT horodatage,
       site_id,
       phase
FROM etat_orbital
"""

REQUETE_ALARMES = """
SELECT a.equipement_id,
       a.horodatage,
       a.type_alarme,
       a.severite
FROM alarme a
JOIN equipement e ON e.equipement_id = a.equipement_id
WHERE e.type_equipement = 'panneau_solaire'
"""

REQUETE_MAINTENANCES = """
SELECT i.equipement_id,
       i.date_debut,
       i.date_fin
FROM intervention i
JOIN equipement e ON e.equipement_id = i.equipement_id
WHERE e.type_equipement = 'panneau_solaire'
"""


def lire(con, requete, dates):
    return pd.read_sql_query(requete, con, parse_dates=dates)


def lire_donnees(chemin_db=DOSSIER_DB / NOM_CONCEPTUEL):
    if not chemin_db.exists():
        raise SystemExit(f"base introuvable : {chemin_db}\nlancez d'abord python etl/load.py")

    with sqlite3.connect(chemin_db) as con:
        equipements  = lire(con, REQUETE_EQUIPEMENTS,  ["date_installation"])
        mesures      = lire(con, REQUETE_MESURES,      ["horodatage"])
        orbite       = lire(con, REQUETE_ORBITE,       ["horodatage"])
        alarmes      = lire(con, REQUETE_ALARMES,      ["horodatage"])
        maintenances = lire(con, REQUETE_MAINTENANCES, ["date_debut", "date_fin"])

    return equipements, mesures, orbite, alarmes, maintenances


# features  uniquement le present et le passe

def ajouter_phase(mesures, equipements, orbite):
    # le site de chaque panneau, pour savoir quelle orbite le concerne
    df = mesures.merge(equipements, on="equipement_id", how="left")

    # l'orbite est donnee toutes les 15 min , on ramene chaque mesure a son creneau
    df["creneau"] = df["horodatage"].dt.floor("15min")
    orbite = orbite.rename(columns={"horodatage": "creneau"})
    df = df.merge(orbite, on=["creneau", "site_id"], how="left")

    # on garde seulement le soleil ,en eclipse, 0 W est normal
    df = df[df["phase"] == "ensoleillement"].copy()
    return df.sort_values(["equipement_id", "horodatage"], ignore_index=True)


def ajouter_age(df):
    df["age_jours"] = (df["horodatage"] - df["date_installation"]).dt.total_seconds() / 86400
    return df


def ajouter_puissance_moyenne_24h(df):
    # moyenne de toutes les mesures des 24 dernieres heures, panneau par panneau
    moyenne = (df.set_index("horodatage")
                 .groupby("equipement_id")["puissance_w"]
                 .rolling(FENETRE, min_periods=1)
                 .mean()
                 .reset_index(name="puissance_moyenne_24h"))
    return df.merge(moyenne, on=["equipement_id", "horodatage"], how="left")


def ajouter_tendance_24h(df):
    # on cherche, pour chaque mesure, la moyenne 24h telle qu'elle etait 24h plus tot
    hier = df[["equipement_id", "horodatage", "puissance_moyenne_24h"]].rename(
        columns={"horodatage": "horodatage_hier", "puissance_moyenne_24h": "moyenne_hier"})
    df["horodatage_hier"] = df["horodatage"] - FENETRE

    df = pd.merge_asof(df.sort_values("horodatage_hier"),
                       hier.sort_values("horodatage_hier"),
                       on="horodatage_hier", by="equipement_id", direction="backward")
    # negatif = la production baisse par rapport a la veille
    df["tendance_24h"] = df["puissance_moyenne_24h"] - df["moyenne_hier"]
    df = df.drop(columns=["horodatage_hier", "moyenne_hier"])
    return df.sort_values(["equipement_id", "horodatage"], ignore_index=True)


def ajouter_alarmes_24h(df, alarmes):
    # numero de chaque alarme pour son panneau : 1, 2, 3... (un compteur cumule)
    a = alarmes.sort_values("horodatage")[["equipement_id", "horodatage"]].copy()
    a["cumul"] = a.groupby("equipement_id").cumcount() + 1

    def cumul_a(instants):
        # nombre d'alarmes deja survenues a chaque instant
        cle = df[["equipement_id"]].assign(instant=instants)
        res = pd.merge_asof(cle.reset_index().sort_values("instant"),
                            a.rename(columns={"horodatage": "instant"}),
                            on="instant", by="equipement_id", direction="backward")
        return res.set_index("index")["cumul"].reindex(df.index).fillna(0)

    # alarmes des 24 dernieres heures = cumul maintenant - cumul il y a 24h
    df["alarmes_24h"] = (cumul_a(df["horodatage"]) - cumul_a(df["horodatage"] - FENETRE)).astype(int)
    return df


def ajouter_heures_depuis_maintenance(df, maintenances):
    m = maintenances[["equipement_id", "date_fin"]].sort_values("date_fin")
    df = pd.merge_asof(df.sort_values("horodatage"), m,
                       left_on="horodatage", right_on="date_fin",
                       by="equipement_id", direction="backward")
    # jamais maintenu -> on compte depuis l'installation
    reference = df["date_fin"].fillna(df["date_installation"])
    df["heures_depuis_maintenance"] = (df["horodatage"] - reference).dt.total_seconds() / 3600
    df = df.drop(columns=["date_fin"])
    return df.sort_values(["equipement_id", "horodatage"], ignore_index=True)


def construire_features(equipements, mesures, orbite, alarmes, maintenances):
    df = ajouter_phase(mesures, equipements, orbite)
    df = ajouter_age(df)
    df = ajouter_puissance_moyenne_24h(df)
    df = ajouter_tendance_24h(df)
    df = ajouter_alarmes_24h(df, alarmes)
    df = ajouter_heures_depuis_maintenance(df, maintenances)
    return df


# affichage de controle

def afficher(nom, df):
    print("=" * 70)
    print(f"{nom}  ->  {df.shape[0]} lignes x {df.shape[1]} colonnes")
    print("=" * 70)
    print(df.head().to_string(index=False))
    print("\nvaleurs manquantes :")
    print(df.isna().sum().to_string())
    print()


if __name__ == "__main__":
    equipements, mesures, orbite, alarmes, maintenances = lire_donnees()

    afficher("EQUIPEMENTS", equipements)
    afficher("MESURES", mesures)
    afficher("ORBITE", orbite)
    afficher("ALARMES", alarmes)
    afficher("MAINTENANCES", maintenances)

    df = construire_features(equipements, mesures, orbite, alarmes, maintenances)
    afficher("FEATURES (soleil uniquement)", df[FEATURES])