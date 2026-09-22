import numpy as np
import pandas as pd


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


def convertir_dates(serie, format_principal):

    ts = pd.to_datetime(serie, format=format_principal, errors="coerce", utc=True)

    reste = ts.isna() & serie.notna()
    if reste.any():
        ts.loc[reste] = pd.to_datetime(
            serie[reste], format="mixed", dayfirst=True, errors="coerce", utc=True
        )
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


def marquer_lignes_vides(df):
    return df.isna().all(axis=1)


def marquer_cle_nulle(df, cles):
    return df[cles].isna().any(axis=1)


def marquer_doublons(df, cles):
    return df.duplicated(subset=cles, keep="first")


def marquer_fk_invalide(serie_enfant, serie_parent):
    return serie_enfant.notna() & ~serie_enfant.isin(set(serie_parent.dropna()))


def marquer_hors_periode(serie_dates, debut, fin):
    debut = pd.Timestamp(debut, tz="UTC")
    fin   = pd.Timestamp(fin,   tz="UTC")
    return serie_dates.notna() & ((serie_dates < debut) | (serie_dates >= fin))


# test
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

    brut = pd.read_csv(config.RAW / "telemetrie.csv", dtype=str, nrows=50000)

    df = normaliser_colonnes(brut)
    df["timestamp"] = convertir_dates(df["timestamp"], "%Y-%m-%dT%H:%M:%S")
    df = convertir_numeriques(
        df, ["puissance_w", "temperature_c", "rayonnement", "tension_v", "courant_a"]
    )
    df, compteurs = neutraliser_bornes(df, config.BORNES["telemetrie"])

    print("dates illisibles (NaT) :", int(df["timestamp"].isna().sum()))
    print("valeurs neutralisees   :", compteurs)
    print("doublons de cle        :",
          int(marquer_doublons(df, ["timestamp", "equipement_id"]).sum()))

    # garde-fou : les dates doivent tomber dans la periode couverte
    hors = marquer_hors_periode(df["timestamp"], config.PERIODE_DEBUT, config.PERIODE_FIN)
    print("dates hors periode     :", int(hors.sum()))
    if hors.any():
        print("\n", pd.DataFrame({
            "chaine_origine": brut.loc[hors, "timestamp"],
            "date_obtenue":   df.loc[hors, "timestamp"],
        }).to_string())

    print("\ntypes obtenus :")
    print(df.dtypes.to_string())
    print("\n", df.head(3).to_string())
