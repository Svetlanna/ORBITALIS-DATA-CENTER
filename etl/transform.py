import pandas as pd

import numpy as np
from config import FORMATS_DATES, PAS_ORBITAL, PHASE_INDETERMINEE, VALEURS_NULLES


def normaliser_colonnes(df):
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(r"[^\w]+", "_", regex=True)
                  .str.strip("_")
    )
    return df


def reparer_heures(serie):

    return serie.str.replace(r"(\d{1,2})h(\d{2})", r"\1:\2", regex=True)


def convertir_dates(serie, format_principal, formats=FORMATS_DATES):

    brut = serie.astype("string").str.strip()
    brut = brut.mask(brut.isin(VALEURS_NULLES))

    ts = pd.to_datetime(brut, format=format_principal, errors="coerce", utc=True)

    for fmt in formats:
        reste = ts.isna() & brut.notna()
        if not reste.any():
            break
        essai = pd.to_datetime(brut[reste], format=fmt, errors="coerce", utc=True).dropna()
        if not essai.empty:
            ts.loc[essai.index] = essai

    return ts


def convertir_numeriques(df, colonnes):

    df = df.copy()
    for c in colonnes:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def neutraliser_bornes(df, bornes):

    df = df.copy()
    compteurs = {}
    for colonne, (mini, maxi) in bornes.items():
        if colonne not in df.columns:
            continue
        hors = df[colonne].notna() & ((df[colonne] < mini) | (df[colonne] > maxi))
        compteurs[colonne] = int(hors.sum())
        df.loc[hors, colonne] = np.nan
    return df, compteurs


def neutraliser_modalites(df, modalites):

    df = df.copy()
    compteurs = {}
    for colonne, autorisees in modalites.items():
        if colonne not in df.columns:
            continue
        hors = df[colonne].notna() & ~df[colonne].isin(autorisees)
        compteurs[colonne] = int(hors.sum())
        df.loc[hors, colonne] = np.nan
    return df, compteurs
def joindre_contexte_orbital(telemetrie, equipements, orbite, pas=PAS_ORBITAL):

    lignes_avant = len(telemetrie)

    # 1. equipement vers site, drop_duplicates protege du doublon EQ-006
    equip = equipements[["equipement_id", "site_id"]].drop_duplicates("equipement_id")
    df = telemetrie.merge(equip, on="equipement_id", how="left")

    # 2. calage sur la grille orbitale, floor et non round
    df["creneau_orbital"] = df["timestamp"].dt.floor(pas)

    # 3. creneau et site vers phase
    contexte = (orbite[["timestamp", "site_id", "phase"]]
                .rename(columns={"timestamp": "creneau_orbital"})
                .drop_duplicates(["creneau_orbital", "site_id"]))
    df = df.merge(contexte, on=["creneau_orbital", "site_id"], how="left")

    # 4. aucune phase ne reste manquante, l indetermine est un etat a part entiere
    df["phase"] = df["phase"].fillna(PHASE_INDETERMINEE)

    assert len(df) == lignes_avant, (
        f"la jointure a change le nombre de lignes, {lignes_avant} -> {len(df)}"
    )
    return df





def joindre_contexte_orbital(telemetrie, equipements, orbite, pas=PAS_ORBITAL):
    lignes_avant = len(telemetrie)

    equip = equipements[["equipement_id", "site_id"]].drop_duplicates("equipement_id")
    df = telemetrie.merge(equip, on="equipement_id", how="left")

    df["creneau_orbital"] = df["timestamp"].dt.floor(pas)

    contexte = (orbite[["timestamp", "site_id", "phase"]]
                .rename(columns={"timestamp": "creneau_orbital"})
                .drop_duplicates(["creneau_orbital", "site_id"]))
    df = df.merge(contexte, on=["creneau_orbital", "site_id"], how="left")

    df["phase"] = df["phase"].fillna(PHASE_INDETERMINEE)

    assert len(df) == lignes_avant, (
        f"la jointure a change le nombre de lignes, {lignes_avant} -> {len(df)}"
    )
    return df


def construire_analytics(telemetrie, equipements, sites, types_producteurs):
    # ajoute deux indicateurs calcules
    # puissance_attendue_w = puissance nominale x rayonnement recu
    # performance          = puissance reelle / puissance attendue
    lignes_avant = len(telemetrie)

    df = telemetrie.merge(
        equipements[["equipement_id", "type", "modele", "puissance_nominale_w"]],
        on="equipement_id", how="left")
    df = df.merge(
        sites[["site_id", "nom", "orbite_type", "altitude_km"]].rename(columns={"nom": "nom_site"}),
        on="site_id", how="left")

    producteur = df["type"].isin(types_producteurs)
    attendue = df["puissance_nominale_w"] * df["rayonnement"]

    df["puissance_attendue_w"] = attendue.where(producteur & (attendue > 0))
    df["performance"] = (df["puissance_w"] / df["puissance_attendue_w"]).replace([np.inf, -np.inf], np.nan)
    df["ecart_w"] = df["puissance_w"] - df["puissance_attendue_w"]
    df["hors_eclipse"] = df["phase"] == "ensoleillement"

    assert len(df) == lignes_avant, f"l assemblage a change le nombre de lignes, {lignes_avant} -> {len(df)}"
    return df