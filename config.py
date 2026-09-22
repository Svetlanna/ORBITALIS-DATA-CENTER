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
BORNES = {
    "telemetrie": {
        "puissance_w": (-700.0, 5000.0),
        "temperature_c": (-150.0, 150.0),
        "tension_v":     (0.0, 100.0),
        "courant_a":     (0.0, 100.0),
        "rayonnement":   (0.0, 1.2),
    },
    "orbite": {
        # constante solaire ~1368 W/m2, marge jusqu'a 1600
        "rayonnement_solaire_w_m2": (0.0, 1600.0),
        "temperature_ambiante_c":   (-150.0, 150.0),
    },
    "equipements": {
        # une puissance negative n'a pas de sens
        "puissance_nominale_w": (0.0, 5000.0),
    },
    "maintenance": {
        "cout_eur": (0.0, 100000.0),
    },
}


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



MOTIF_DATE_HORS_PERIODE = "DATE_HORS_PERIODE"


FORMATS_DATES = [
    "%Y-%m-%dT%H:%M:%S",         # telemetrie,
    "%Y-%m-%d %H:%M:%S",         # orbite et alarmes
    "%Y-%m-%dT%H:%M:%S%z",       # iso avec decalage explicite
    "%Y-%m-%d %H:%M:%S.%f%z",    # telemetrie
    "%Y-%m-%d %H:%M:%S.%f",      # fractions sans decalage
    "%Y-%m-%d %H:%M",            # minute seulement
    "%Y-%m-%d",                  # maintenance et equipements
    "%Y/%m/%d %H:%M",            # telemetrie exotique
    "%Y/%m/%d %Hh%M",            # alarmes exotique, separateur h
    "%Y/%m/%d",
    "%d/%m/%Y %H:%M",            # telemetrie exotique
    "%d/%m/%Y",                  # equipements exotique
    "%d-%m-%Y",                  # maintenance exotique
]


VALEURS_NULLES = {
    "", "nan", "NaN", "NAN", "NA", "N/A", "na",
    "null", "NULL", "Null", "None", "none", "NONE",
    "-", "--", "?", "??", "???", "inconnu", "UNKNOWN", "unknown",
}


DTYPE_DATE = "datetime64[us, UTC]"


PERIODE_DEBUT = pd.Timestamp("2025-05-01 00:00:00", tz=FUSEAU)
PERIODE_FIN   = pd.Timestamp("2025-06-15 00:00:00", tz=FUSEAU)

#  dates
COLONNES_DATES = {
    "telemetrie":  ["timestamp", "creneau_orbital"],
    "orbite":      ["timestamp"],
    "alarmes":     ["timestamp"],
    "maintenance": ["date_debut", "date_fin"],
    "equipements": ["date_installation"],
    "sites":       ["date_mise_en_service"],
}

PHASE_INDETERMINEE = "indetermine"
PAS_ORBITAL = "15min"

TYPES_PRODUCTEURS = ["panneau_solaire"]

MOTIF_INTERVALLE_INVALIDE = "INTERVALLE_INVALIDE"
