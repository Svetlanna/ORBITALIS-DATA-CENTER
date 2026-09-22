
import pandas as pd

from config import (
    MOTIF_CLE_DUPLIQUEE, MOTIF_CLE_NULLE, MOTIF_DATE_HORS_PERIODE,
    MOTIF_DATE_ILLISIBLE, MOTIF_FK_INVALIDE, MOTIF_LIGNE_VIDE,
    PERIODE_DEBUT, PERIODE_FIN,
)



def ligne_vide():

    return lambda df: df.isna().all(axis=1)


def cle_nulle(colonnes):

    return lambda df: df[colonnes].isna().any(axis=1)


def cle_dupliquee(colonnes, garder="first"):

    return lambda df: df.duplicated(subset=colonnes, keep=garder)


def fk_invalide(colonne, valeurs_valides, rejeter_nuls=False):


    valides = set(valeurs_valides)

    def _masque(df):
        hors = ~df[colonne].isin(valides)
        return hors if rejeter_nuls else (df[colonne].notna() & hors)

    return _masque


def date_illisible(colonne):

    return lambda df: df[colonne].isna()


def date_hors_periode(colonne, debut=PERIODE_DEBUT, fin=PERIODE_FIN):

    return lambda df: df[colonne].notna() & ((df[colonne] < debut) | (df[colonne] >= fin))


#  moteur

def appliquer_controles(df, controles, source):
    lues = len(df)
    restants = df.copy()
    restants["_ligne_source"] = df.index
    morceaux = []
    detail = {}

    for motif, fonction in controles:
        if restants.empty:
            detail[motif] = 0
            continue
        masque = fonction(restants).fillna(False).astype(bool)
        detail[motif] = int(masque.sum())
        if masque.any():
            sortis = restants[masque].copy()
            sortis["_motif_rejet"] = motif
            sortis["_source"] = source
            morceaux.append(sortis)
        restants = restants[~masque]

    rejetes = (pd.concat(morceaux, ignore_index=True) if morceaux
               else pd.DataFrame(columns=list(df.columns) + ["_ligne_source", "_motif_rejet", "_source"]))
    acceptes = restants.drop(columns="_ligne_source")

    indicateurs = {
        "source": source,
        "lignes_lues": lues,
        "lignes_acceptees": len(acceptes),
        "lignes_rejetees": len(rejetes),
        "doublons_detectes": detail.get(MOTIF_CLE_DUPLIQUEE, 0),
        "detail_par_motif": detail,
    }

    # equation d audit, aucune ligne ne doit disparaitre ni apparaitre
    assert lues == len(acceptes) + len(rejetes), (
        f"{source} perte de lignes, {lues} lues mais "
        f"{len(acceptes)} acceptees + {len(rejetes)} rejetees"
    )

    return acceptes, rejetes, indicateurs

def intervalle_invalide(debut, fin):
    
    return lambda df: df[debut].notna() & df[fin].notna() & (df[fin] < df[debut])