import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C

DOSSIER_DB    = C.RACINE / "data" / "db"
NOM_CONCEPTUEL = "orbitalis_conceptuel.db"
NOM_ETOILE     = "orbitalis_etoile.db"

# hypothese documentee
# la telemetrie arrive toutes les 5 minutes, une mesure de puissance (W)
# represente donc 5/60 h d'energie (Wh)
PAS_MESURE_H = 5 / 60

# une phase d'eclipse n'est pas une panne, on n'y attend aucune production
PHASES = {"ensoleillement": 1, "eclipse": 0, C.PHASE_INDETERMINEE: None}

FORMAT_DATETIME = "%Y-%m-%d %H:%M:%S"
FORMAT_DATE     = "%Y-%m-%d"


#  schemas SQLite

DDL_CONCEPTUEL = """
CREATE TABLE site (
    site_id              TEXT PRIMARY KEY,
    nom                  TEXT,
    orbite_type          TEXT,
    altitude_km          REAL,
    inclination_deg      REAL,
    date_mise_en_service TEXT,
    statut               TEXT,
    description          TEXT,
    capacite_max_kw      REAL,
    zone_orbitale        TEXT
);

CREATE TABLE modele (
    modele_id            TEXT PRIMARY KEY,
    type_equipement      TEXT,
    fabricant            TEXT,
    puissance_nominale_w REAL,
    rendement_nominal    REAL,
    duree_vie_annees     INTEGER,
    masse_kg             REAL
);

CREATE TABLE type_alarme (
    type_alarme    TEXT PRIMARY KEY,
    seuil_warning  REAL,
    seuil_critical REAL,
    unite          TEXT,
    description    TEXT
);

CREATE TABLE equipement (
    equipement_id        TEXT PRIMARY KEY,
    site_id              TEXT NOT NULL REFERENCES site (site_id),
    type_equipement      TEXT,
    modele_id            TEXT REFERENCES modele (modele_id),
    puissance_nominale_w REAL,
    date_installation    TEXT,
    statut               TEXT
);

CREATE TABLE etat_orbital (
    horodatage               TEXT NOT NULL,
    site_id                  TEXT NOT NULL REFERENCES site (site_id),
    phase                    TEXT,
    rayonnement_solaire_w_m2 REAL,
    temperature_ambiante_c   REAL,
    PRIMARY KEY (horodatage, site_id)
);

CREATE TABLE mesure (
    horodatage    TEXT NOT NULL,
    equipement_id TEXT NOT NULL REFERENCES equipement (equipement_id),
    puissance_w   REAL,
    temperature_c REAL,
    tension_v     REAL,
    courant_a     REAL,
    rayonnement   REAL,
    PRIMARY KEY (horodatage, equipement_id)
);

CREATE TABLE alarme (
    alarme_id     TEXT PRIMARY KEY,
    equipement_id TEXT NOT NULL REFERENCES equipement (equipement_id),
    type_alarme   TEXT NOT NULL REFERENCES type_alarme (type_alarme),
    horodatage    TEXT,
    severite      TEXT,
    message       TEXT,
    acquittee     INTEGER
);

CREATE TABLE intervention (
    maintenance_id    TEXT PRIMARY KEY,
    equipement_id     TEXT NOT NULL REFERENCES equipement (equipement_id),
    date_debut        TEXT,
    date_fin          TEXT,
    type_intervention TEXT,
    technicien        TEXT,
    cout_eur          REAL,
    commentaire       TEXT
);
"""

DDL_ETOILE = """
CREATE TABLE dim_site (
    id_site         INTEGER PRIMARY KEY,
    site_id         TEXT NOT NULL,
    nom             TEXT,
    orbite_type     TEXT,
    altitude_km     REAL,
    inclination_deg REAL,
    capacite_max_kw REAL,
    zone_orbitale   TEXT,
    description     TEXT,
    statut          TEXT
);

CREATE TABLE dim_modele (
    id_modele            INTEGER PRIMARY KEY,
    modele_id            TEXT,
    type_equipement      TEXT,
    fabricant            TEXT,
    puissance_nominale_w REAL,
    rendement_nominal    REAL,
    duree_vie_annees     INTEGER,
    masse_kg             REAL
);

CREATE TABLE dim_equipement (
    id_equipement        INTEGER PRIMARY KEY,
    equipement_id        TEXT,
    id_site              INTEGER REFERENCES dim_site (id_site),
    id_modele            INTEGER REFERENCES dim_modele (id_modele),
    modele_code          TEXT,
    type_equipement      TEXT,
    puissance_nominale_w REAL,
    est_producteur       INTEGER,
    statut               TEXT,
    date_installation    TEXT
);

CREATE TABLE dim_phase (
    id_phase            INTEGER PRIMARY KEY,
    phase               TEXT NOT NULL,
    production_attendue INTEGER
);

CREATE TABLE dim_temps (
    id_temps        INTEGER PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    date            TEXT,
    annee           INTEGER,
    mois            INTEGER,
    jour            INTEGER,
    heure           INTEGER,
    minute          INTEGER,
    jour_semaine    INTEGER,
    semaine         INTEGER,
    creneau_orbital TEXT
);

CREATE TABLE dim_type_alarme (
    id_type_alarme INTEGER PRIMARY KEY,
    type_alarme    TEXT,
    seuil_warning  REAL,
    seuil_critical REAL,
    unite          TEXT,
    description    TEXT
);

CREATE TABLE fait_mesure (
    id_temps             INTEGER NOT NULL REFERENCES dim_temps (id_temps),
    id_equipement        INTEGER NOT NULL REFERENCES dim_equipement (id_equipement),
    id_site              INTEGER REFERENCES dim_site (id_site),
    id_phase             INTEGER REFERENCES dim_phase (id_phase),
    puissance_w          REAL,
    temperature_c        REAL,
    tension_v            REAL,
    courant_a            REAL,
    rayonnement          REAL,
    puissance_attendue_w REAL,
    performance          REAL,
    ecart_w              REAL,
    energie_wh           REAL,
    energie_attendue_wh  REAL,
    perte_wh             REAL,
    PRIMARY KEY (id_temps, id_equipement)
);

CREATE TABLE fait_alarme (
    alarme_id      TEXT PRIMARY KEY,
    id_temps       INTEGER REFERENCES dim_temps (id_temps),
    id_equipement  INTEGER REFERENCES dim_equipement (id_equipement),
    id_type_alarme INTEGER REFERENCES dim_type_alarme (id_type_alarme),
    severite       TEXT,
    est_critique   INTEGER,
    acquittee      INTEGER
);

CREATE TABLE fait_maintenance (
    maintenance_id    TEXT PRIMARY KEY,
    id_equipement     INTEGER REFERENCES dim_equipement (id_equipement),
    id_temps_debut    INTEGER REFERENCES dim_temps (id_temps),
    id_temps_fin      INTEGER REFERENCES dim_temps (id_temps),
    type_intervention TEXT,
    technicien        TEXT,
    cout_eur          REAL,
    duree_jours       REAL
);
"""


#  outils

def lire(nom, dossier=C.CLEANED):
    return pd.read_csv(dossier / f"{nom}.csv", encoding="utf-8")


def en_datetime(serie):
    return pd.to_datetime(serie, utc=True, errors="coerce")


def texte_datetime(serie):
    return en_datetime(serie).dt.strftime(FORMAT_DATETIME)


def texte_date(serie):
    return en_datetime(serie).dt.strftime(FORMAT_DATE)


def creer_base(chemin, ddl):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if chemin.exists():
        chemin.unlink()
    con = sqlite3.connect(chemin)
    # sqlite ne verifie les cles etrangeres que si on le lui demande, connexion par connexion
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ddl)
    return con


def separer_invalides(df, nom, non_nuls=(), fks=()):
    # le modele interdit certaines lignes que le nettoyage a laissees passer
    # fks est une liste de (colonne, valeurs autorisees), un NULL reste accepte
    valide = pd.Series(True, index=df.index)
    for colonne in non_nuls:
        valide &= df[colonne].notna()
    for colonne, autorisees in fks:
        valide &= df[colonne].isna() | df[colonne].isin(autorisees)

    rejetes = df[~valide]
    if not rejetes.empty:
        print(f"    {nom}: {len(rejetes)} ligne(s) ecartee(s) au chargement")
    return df[valide], rejetes.assign(_table=nom)


def inserer(con, table, df):
    # NaN / NaT -> None, que sqlite enregistre comme NULL
    df = df.astype(object).where(df.notna(), None)
    colonnes = ", ".join(df.columns)
    marques = ", ".join("?" * len(df.columns))
    con.executemany(f"INSERT INTO {table} ({colonnes}) VALUES ({marques})",
                    df.itertuples(index=False, name=None))
    print(f"    {table:20} {len(df):>8} lignes")


def cle_substitution(valeurs):
    # cle technique 1..n pour chaque valeur metier distincte
    valeurs = pd.Series(valeurs).dropna().drop_duplicates().sort_values().tolist()
    return {valeur: i for i, valeur in enumerate(valeurs, start=1)}


def verifier(con):
    erreurs = con.execute("PRAGMA foreign_key_check").fetchall()
    assert not erreurs, f"cles etrangeres invalides : {erreurs[:5]}"


#  preparation commune

def preparer_conceptuel():
    """Lit cleaned et renomme les colonnes selon le modele conceptuel."""
    modele = lire("catalogue_modeles")
    type_alarme = lire("catalogue_seuils_alarmes")

    site = lire("sites").merge(lire("catalogue_references_sites"), on="site_id", how="left")
    site["date_mise_en_service"] = texte_date(site["date_mise_en_service"])

    equipement = lire("equipements").rename(columns={"type": "type_equipement", "modele": "modele_id"})
    equipement["date_installation"] = texte_date(equipement["date_installation"])

    etat_orbital = lire("orbite").rename(columns={"timestamp": "horodatage"})
    etat_orbital["horodatage"] = texte_datetime(etat_orbital["horodatage"])

    mesure = lire("telemetrie").rename(columns={"timestamp": "horodatage"})
    mesure = mesure[["horodatage", "equipement_id", "puissance_w", "temperature_c",
                     "tension_v", "courant_a", "rayonnement"]]
    mesure["horodatage"] = texte_datetime(mesure["horodatage"])

    alarme = lire("alarmes").rename(columns={"timestamp": "horodatage"})
    alarme["horodatage"] = texte_datetime(alarme["horodatage"])
    alarme["acquittee"] = alarme["acquittee"].map({True: 1, False: 0})
    alarme = alarme[["alarme_id", "equipement_id", "type_alarme", "horodatage",
                     "severite", "message", "acquittee"]]

    intervention = lire("maintenance")
    intervention["date_debut"] = texte_date(intervention["date_debut"])
    intervention["date_fin"] = texte_date(intervention["date_fin"])

    # controles du modele, dans l'ordre parent -> enfant
    rejets = []
    equipement, r = separer_invalides(equipement, "equipement", non_nuls=["site_id"],
                                      fks=[("site_id", site["site_id"]),
                                           ("modele_id", modele["modele_id"])])
    rejets.append(r)
    ids = equipement["equipement_id"]
    etat_orbital, r = separer_invalides(etat_orbital, "etat_orbital", non_nuls=["site_id"],
                                      fks=[("site_id", site["site_id"])])
    rejets.append(r)
    mesure, r = separer_invalides(mesure, "mesure", non_nuls=["equipement_id"], fks=[("equipement_id", ids)])
    rejets.append(r)
    alarme, r = separer_invalides(alarme, "alarme", non_nuls=["equipement_id", "type_alarme"],
                                  fks=[("equipement_id", ids),
                                       ("type_alarme", type_alarme["type_alarme"])])
    rejets.append(r)
    intervention, r = separer_invalides(intervention, "intervention", non_nuls=["equipement_id"],
                                      fks=[("equipement_id", ids)])
    rejets.append(r)

    tables = {"site": site, "modele": modele, "type_alarme": type_alarme,
              "equipement": equipement, "etat_orbital": etat_orbital, "mesure": mesure,
              "alarme": alarme, "intervention": intervention}
    return tables, pd.concat(rejets, ignore_index=True)


#  base conceptuelle

def charger_conceptuel(tables, chemin):
    print(f"\n  base conceptuelle -> {chemin.name}")
    con = creer_base(chemin, DDL_CONCEPTUEL)
    with con:  # une transaction, tout ou rien
        for nom in ["site", "modele", "type_alarme", "equipement",
                    "etat_orbital", "mesure", "alarme", "intervention"]:
            inserer(con, nom, tables[nom])
    verifier(con)
    con.close()


#  base en etoile

def construire_dim_temps(*series):
    instants = pd.concat([en_datetime(s) for s in series]).dropna().drop_duplicates().sort_values()
    instants = instants.reset_index(drop=True)
    iso = instants.dt.isocalendar()
    return pd.DataFrame({
        "id_temps":        range(1, len(instants) + 1),
        "timestamp":       instants.dt.strftime(FORMAT_DATETIME),
        "date":            instants.dt.strftime(FORMAT_DATE),
        "annee":           instants.dt.year,
        "mois":            instants.dt.month,
        "jour":            instants.dt.day,
        "heure":           instants.dt.hour,
        "minute":          instants.dt.minute,
        "jour_semaine":    instants.dt.dayofweek + 1,  # 1 = lundi
        "semaine":         iso["week"].astype(int),
        "creneau_orbital": instants.dt.floor(C.PAS_ORBITAL).dt.strftime(FORMAT_DATETIME),
    })


def charger_etoile(tables, chemin):
    print(f"\n  base en etoile -> {chemin.name}")
    analytics = lire("mesures_enrichies", C.ANALYTICS)

    #  dimensions, chaque cle metier recoit une cle technique entiere
    site = tables["site"]
    id_site = cle_substitution(site["site_id"])
    dim_site = site.assign(id_site=site["site_id"].map(id_site))[
        ["id_site", "site_id", "nom", "orbite_type", "altitude_km", "inclination_deg",
         "capacite_max_kw", "zone_orbitale", "description", "statut"]]

    modele = tables["modele"]
    id_modele = cle_substitution(modele["modele_id"])
    dim_modele = modele.assign(id_modele=modele["modele_id"].map(id_modele))[
        ["id_modele", "modele_id", "type_equipement", "fabricant", "puissance_nominale_w",
         "rendement_nominal", "duree_vie_annees", "masse_kg"]]

    equipement = tables["equipement"]
    id_equipement = cle_substitution(equipement["equipement_id"])
    dim_equipement = pd.DataFrame({
        "id_equipement":        equipement["equipement_id"].map(id_equipement),
        "equipement_id":        equipement["equipement_id"],
        "id_site":              equipement["site_id"].map(id_site),
        "id_modele":            equipement["modele_id"].map(id_modele),
        "modele_code":          equipement["modele_id"],
        "type_equipement":      equipement["type_equipement"],
        "puissance_nominale_w": equipement["puissance_nominale_w"],
        "est_producteur":       equipement["type_equipement"].isin(C.TYPES_PRODUCTEURS).astype(int),
        "statut":               equipement["statut"],
        "date_installation":    equipement["date_installation"],
    })

    id_phase = {phase: i for i, phase in enumerate(PHASES, start=1)}
    dim_phase = pd.DataFrame({"id_phase": list(id_phase.values()),
                              "phase": list(id_phase.keys()),
                              "production_attendue": list(PHASES.values())})

    seuils = tables["type_alarme"]
    id_type_alarme = cle_substitution(seuils["type_alarme"])
    dim_type_alarme = seuils.assign(id_type_alarme=seuils["type_alarme"].map(id_type_alarme))[
        ["id_type_alarme", "type_alarme", "seuil_warning", "seuil_critical", "unite", "description"]]

    alarme, maintenance = tables["alarme"], tables["intervention"]
    dim_temps = construire_dim_temps(analytics["timestamp"], alarme["horodatage"],
                                     maintenance["date_debut"], maintenance["date_fin"])
    id_temps = dict(zip(dim_temps["timestamp"], dim_temps["id_temps"]))

    #  faits
    analytics = analytics[analytics["equipement_id"].isin(id_equipement)]
    fait_mesure = pd.DataFrame({
        "id_temps":             texte_datetime(analytics["timestamp"]).map(id_temps),
        "id_equipement":        analytics["equipement_id"].map(id_equipement),
        "id_site":              analytics["site_id"].map(id_site),
        "id_phase":             analytics["phase"].map(id_phase),
        "puissance_w":          analytics["puissance_w"],
        "temperature_c":        analytics["temperature_c"],
        "tension_v":            analytics["tension_v"],
        "courant_a":            analytics["courant_a"],
        "rayonnement":          analytics["rayonnement"],
        "puissance_attendue_w": analytics["puissance_attendue_w"],
        "performance":          analytics["performance"],
        "ecart_w":              analytics["ecart_w"],
        "energie_wh":           analytics["puissance_w"] * PAS_MESURE_H,
        "energie_attendue_wh":  analytics["puissance_attendue_w"] * PAS_MESURE_H,
    })
    # perte positive = moins produit que prevu, negative = surproduction
    fait_mesure["perte_wh"] = fait_mesure["energie_attendue_wh"] - fait_mesure["energie_wh"]

    fait_alarme = pd.DataFrame({
        "alarme_id":      alarme["alarme_id"],
        "id_temps":       alarme["horodatage"].map(id_temps),
        "id_equipement":  alarme["equipement_id"].map(id_equipement),
        "id_type_alarme": alarme["type_alarme"].map(id_type_alarme),
        "severite":       alarme["severite"],
        "est_critique":   (alarme["severite"] == "critical").astype(int),
        "acquittee":      alarme["acquittee"],
    })

    debut = en_datetime(maintenance["date_debut"])
    fin = en_datetime(maintenance["date_fin"])
    fait_maintenance = pd.DataFrame({
        "maintenance_id":    maintenance["maintenance_id"],
        "id_equipement":     maintenance["equipement_id"].map(id_equipement),
        "id_temps_debut":    debut.dt.strftime(FORMAT_DATETIME).map(id_temps),
        "id_temps_fin":      fin.dt.strftime(FORMAT_DATETIME).map(id_temps),
        "type_intervention": maintenance["type_intervention"],
        "technicien":        maintenance["technicien"],
        "cout_eur":          maintenance["cout_eur"],
        "duree_jours":       (fin - debut).dt.total_seconds() / 86400,
    })

    con = creer_base(chemin, DDL_ETOILE)
    with con:
        for nom, df in [("dim_site", dim_site), ("dim_modele", dim_modele),
                        ("dim_equipement", dim_equipement), ("dim_phase", dim_phase),
                        ("dim_type_alarme", dim_type_alarme), ("dim_temps", dim_temps),
                        ("fait_mesure", fait_mesure), ("fait_alarme", fait_alarme),
                        ("fait_maintenance", fait_maintenance)]:
            inserer(con, nom, df)
    verifier(con)
    con.close()


#  orchestration

def executer(dossier_db=DOSSIER_DB):
    print("chargement, cleaned + analytics -> sqlite")
    print("\n  controles du modele")
    tables, rejets = preparer_conceptuel()

    charger_conceptuel(tables, dossier_db / NOM_CONCEPTUEL)
    charger_etoile(tables, dossier_db / NOM_ETOILE)

    if not rejets.empty:
        C.REJETS.mkdir(parents=True, exist_ok=True)
        rejets.to_csv(C.REJETS / "rejets_chargement.csv", index=False, encoding="utf-8")
    print(f"\n  bases dans {dossier_db}")


if __name__ == "__main__":
    executer()