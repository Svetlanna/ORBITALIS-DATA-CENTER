import pandas as pd
from pathlib import Path

# chemins
RACINE    = Path(__file__).resolve().parent
RAW       = RACINE / "data" / "raw"
CLEANED   = RACINE / "data" / "cleaned"
ANALYTICS = RACINE / "data" / "analytics"
REJETS    = RACINE / "data" / "rejets"
QUALITY   = RACINE / "data" / "quality"

#hypothese documentee
# aucune source ne porte d'indication de fuseau horaire
# tous les horodatages sont SUPPOSES etre en UTC
FUSEAU = "UTC"

# bornes de plausibilite physique
# toute valeur hors bornes est NEUTRALISEE (remplacee par NaN)
# la ligne elle-meme est conservee
BORNES = {
    "telemetrie": {
        # nominal max au catalogue = 2500 W ; marge x2
        "puissance_w":   (-100.0, 5000.0),
        # surfaces en orbite basse : de -150 a +120 degres environ
        "temperature_c": (-150.0, 150.0),
        # nominal 48 V, plage observee 37-58
        "tension_v":     (0.0, 100.0),
        "courant_a":     (0.0, 100.0),
        # ratio sans unite, plage observee 0 - 1.148
        "rayonnement":   (0.0, 1.2),
    },
    "orbite": {
        # constante solaire ~1368 W/m2, marge jusqu'a 1600
        "rayonnement_solaire_w_m2": (0.0, 1600.0),
        "temperature_ambiante_c":   (-150.0, 150.0),
    },
    "equipements": {
        # une puissance nominale negative n'a pas de sens
        "puissance_nominale_w": (0.0, 5000.0),
    },
    "maintenance": {
        # un cout d'intervention ne peut pas etre negatif
        "cout_eur": (0.0, 100000.0),
    },
}

# --- modalites autorisees ----------------------------------------------
# hors liste -> NaN (valeur inconnue), la ligne est conservee
MODALITES = {
    "equipements": {
        "type":   ["panneau_solaire", "convertisseur_DC", "batterie",
                   "onduleur", "radiateur"],
        "statut": ["operationnel", "degrade", "maintenance"],
    },
    "orbite": {
        "phase": ["ensoleillement", "eclipse"],
    },
    "alarmes": {
        "severite":    ["info", "warning", "critical"],
        "type_alarme": ["surchauffe", "sous_tension", "perte_puissance",
                        "surcharge", "capteur_defaillant", "vibration_anormale"],
    },
    "maintenance": {
        "type_intervention": ["inspection", "remplacement", "preventive",
                              "calibration", "corrective"],
    },
}

#   motifs de rejet (codes controles, jamais du texte libre)
MOTIF_LIGNE_VIDE     = "LIGNE_VIDE"
MOTIF_CLE_NULLE      = "CLE_NULLE"
MOTIF_CLE_DUPLIQUEE  = "CLE_DUPLIQUEE"
MOTIF_FK_INVALIDE    = "FK_INVALIDE"
MOTIF_DATE_ILLISIBLE = "DATE_ILLISIBLE"