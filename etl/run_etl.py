import sys
from pathlib import Path

import pandas as pd

# la racine doit etre sur le chemin AVANT tout import du projet
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C
from etl.extract import lire_toutes_les_sources
from etl.quality import (appliquer_controles, cle_dupliquee, cle_nulle,
                         date_hors_periode, date_illisible, fk_invalide,
                         intervalle_invalide, ligne_vide)
from etl.transform import (construire_analytics, convertir_dates, convertir_numeriques,
                           joindre_contexte_orbital, neutraliser_bornes,
                           neutraliser_modalites, normaliser_colonnes, reparer_heures)

#  declaration des sources
# une entree par source, la regle sort du code
# cle        colonnes qui identifient une ligne de facon unique et non nulle
# dates      colonne -> format principal, le repli gere les formats exotiques
# periode    True si les dates doivent tomber dans la periode couverte
#            False pour les referentiels, une installation de 2024 est legitime
# numeriques colonnes a forcer en nombre
# parent     (colonne enfant, source parente, colonne parente) pour l integrite referentielle

SOURCES = {
    "sites": {
        "cle": ["site_id"],
        "dates": {"date_mise_en_service": "%Y-%m-%d"},
        "periode": False,
        "numeriques": ["altitude_km", "inclination_deg"],
        "parent": None,
    },
    "equipements": {
        "cle": ["equipement_id"],
        "dates": {"date_installation": "%Y-%m-%d"},
        "periode": False,
        "numeriques": ["puissance_nominale_w"],
        "parent": ("site_id", "sites", "site_id"),
    },
    "orbite": {
        "cle": ["timestamp", "site_id"],
        "dates": {"timestamp": "%Y-%m-%d %H:%M:%S"},
        "periode": True,
        "numeriques": ["rayonnement_solaire_w_m2", "temperature_ambiante_c"],
        "parent": ("site_id", "sites", "site_id"),
    },
    "telemetrie": {
        "cle": ["timestamp", "equipement_id"],
        "dates": {"timestamp": "%Y-%m-%dT%H:%M:%S"},
        "periode": True,
        "numeriques": ["puissance_w", "temperature_c", "rayonnement", "tension_v", "courant_a"],
        "parent": ("equipement_id", "equipements", "equipement_id"),
    },
    "alarmes": {
        "cle": ["alarme_id"],
        "dates": {"timestamp": "%Y-%m-%d %H:%M:%S"},
        "periode": True,
        "numeriques": [],
        "parent": ("equipement_id", "equipements", "equipement_id"),
    },
    "maintenance": {
        "cle": ["maintenance_id"],
        "dates": {"date_debut": "%Y-%m-%d", "date_fin": "%Y-%m-%d"},
        "periode": False,
        "numeriques": ["cout_eur"],
        "parent": ("equipement_id", "equipements", "equipement_id"),
        "fk_rejeter_nuls": True,
        "intervalle": ("date_debut", "date_fin"),
    },
    "catalogue_modeles": {
        "cle": ["modele_id"], "dates": {}, "periode": False,
        "numeriques": ["puissance_nominale_w", "rendement_nominal", "duree_vie_annees", "masse_kg"],
        "parent": None,
    },
    "catalogue_seuils_alarmes": {
        "cle": ["type_alarme"], "dates": {}, "periode": False,
        "numeriques": ["seuil_warning", "seuil_critical"], "parent": None,
    },
    "catalogue_references_sites": {
        "cle": ["site_id"], "dates": {}, "periode": False,
        "numeriques": ["capacite_max_kw"], "parent": None,
    },
}

ORDRE = ["sites", "equipements", "orbite", "telemetrie", "alarmes", "maintenance",
         "catalogue_modeles", "catalogue_seuils_alarmes", "catalogue_references_sites"]


# ------------------------------------------------------------------ etapes

def transformer(df, nom, regle):
    df = normaliser_colonnes(df)

    for colonne, format_principal in regle["dates"].items():
        if colonne in df.columns:
            df[colonne] = convertir_dates(reparer_heures(df[colonne]), format_principal)

    df = convertir_numeriques(df, regle["numeriques"])

    df, bornes_neutralisees = neutraliser_bornes(df, C.BORNES.get(nom, {}))
    df, modalites_neutralisees = neutraliser_modalites(df, C.MODALITES.get(nom, {}))

    return df, {**bornes_neutralisees, **modalites_neutralisees}


def construire_controles(df, nom, regle, referentiels):
    controles = [(C.MOTIF_LIGNE_VIDE, ligne_vide())]

    for colonne in regle["dates"]:
        if colonne in df.columns and colonne in regle["cle"]:
            controles.append((C.MOTIF_DATE_ILLISIBLE, date_illisible(colonne)))

    controles.append((C.MOTIF_CLE_NULLE, cle_nulle(regle["cle"])))

    if regle["periode"]:
        for colonne in regle["dates"]:
            if colonne in df.columns:
                controles.append((C.MOTIF_DATE_HORS_PERIODE, date_hors_periode(colonne)))

    if regle.get("intervalle"):
        debut, fin = regle["intervalle"]
        if debut in df.columns and fin in df.columns:
            controles.append((C.MOTIF_INTERVALLE_INVALIDE, intervalle_invalide(debut, fin)))

    controles.append((C.MOTIF_CLE_DUPLIQUEE, cle_dupliquee(regle["cle"])))

    if regle["parent"]:
        enfant, source_parente, colonne_parente = regle["parent"]
        parent = referentiels.get(source_parente)
        if parent is not None and enfant in df.columns:
            controles.append((C.MOTIF_FK_INVALIDE,
                              fk_invalide(enfant, parent[colonne_parente].dropna(),
                                          rejeter_nuls=regle.get("fk_rejeter_nuls", False))))
    return controles


#orchestration

def executer(dossier_raw=None, echantillon=None):
    dossier_raw = dossier_raw or C.RAW
    for dossier in (C.CLEANED, C.REJETS, C.QUALITY):
        dossier.mkdir(parents=True, exist_ok=True)

    brutes = lire_toutes_les_sources(dossier_raw, echantillon=echantillon)
    propres, tous_rejets, tous_indicateurs, neutralisations = {}, [], [], []

    for nom in ORDRE:
        if nom not in brutes:
            continue
        regle = SOURCES[nom]
        df, neutralises = transformer(brutes[nom], nom, regle)

        if nom == "telemetrie":
            df = joindre_contexte_orbital(df, propres["equipements"], propres["orbite"])

        controles = construire_controles(df, nom, regle, propres)
        acceptes, rejetes, indicateurs = appliquer_controles(df, controles, nom)

        propres[nom] = acceptes
        if not rejetes.empty:
            tous_rejets.append(rejetes)
        tous_indicateurs.append({k: v for k, v in indicateurs.items() if k != "detail_par_motif"})
        for colonne, n in neutralises.items():
            if n:
                neutralisations.append({"source": nom, "colonne": colonne, "valeurs_neutralisees": n})

        acceptes.to_csv(C.CLEANED / f"{nom}.csv", index=False, encoding="utf-8")
        print(f"  {nom:28} {indicateurs['lignes_lues']:>8} lues  "
              f"{indicateurs['lignes_acceptees']:>8} acceptees  "
              f"{indicateurs['lignes_rejetees']:>6} rejetees")

    # zone analytics, la table prete a analyser
    analytics = construire_analytics(propres["telemetrie"], propres["equipements"],
                                     propres["sites"], C.TYPES_PRODUCTEURS)
    C.ANALYTICS.mkdir(parents=True, exist_ok=True)
    analytics.to_csv(C.ANALYTICS / "mesures_enrichies.csv", index=False, encoding="utf-8")
    print(f"\n  analytics {len(analytics)} lignes x {len(analytics.columns)} colonnes, "
          f"performance calculable sur {int(analytics['performance'].notna().sum())}")

    if tous_rejets:
        pd.concat(tous_rejets, ignore_index=True).to_csv(
            C.REJETS / "rejets.csv", index=False, encoding="utf-8")
    pd.DataFrame(tous_indicateurs).to_csv(
        C.QUALITY / "indicateurs_par_source.csv", index=False, encoding="utf-8")
    pd.DataFrame(neutralisations).to_csv(
        C.QUALITY / "neutralisations.csv", index=False, encoding="utf-8")

    return propres, tous_indicateurs


if __name__ == "__main__":
    print("chaine ETL, raw -> cleaned\n")
    propres, indicateurs = executer()
    total = pd.DataFrame(indicateurs).sum(numeric_only=True)
    print(f"\n  TOTAL {int(total.lignes_lues)} lues = "
          f"{int(total.lignes_acceptees)} acceptees + {int(total.lignes_rejetees)} rejetees")
    print(f"\n  cleaned  {C.CLEANED}\n  rejets   {C.REJETS}\n  quality  {C.QUALITY}")