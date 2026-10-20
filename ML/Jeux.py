#
# ML/Jeux.py
# ----------
# Construit la cible "a_risque" et decoupe les donnees en train / validation / test.
#
# C'est EXACTEMENT la meme logique que dans ML/Train.py, mais rangee dans une
# fonction. Pourquoi ? Parce que deux scripts en ont besoin :
#   - ML/Entrainer_versions.py  (pour entrainer les modeles)
#   - ML/MLOPS.py               (pour les comparer sur le MEME jeu de test)
# Si chacun recalculait la cible a sa facon, la comparaison ne serait pas juste.
#

import pandas as pd

from Preparation import FEATURES, construire_features, lire_donnees

# Dates de decoupage (identiques a Train.py)
FIN_TRAIN = pd.Timestamp("2025-05-31")
FIN_VALIDATION = pd.Timestamp("2025-06-07")
MARGE = pd.Timedelta("12h")   # trou de 12 h pour que la cible du train ne "voie" pas la validation


def construire_cible(df, alarmes):
    """Ajoute la colonne a_risque (1 = panneau a risque dans les 12 h suivantes)."""
    df = df.copy()
    alarmes = alarmes.copy()

    # chaque mesure appartient a une periode orbitale de 2 h
    df["periode"] = df["horodatage"].dt.floor("2h")
    df["attendu_w"] = (df["puissance_nominale_w"] * df["rayonnement"]).where(df["puissance_w"].notna())

    # un resume par panneau et par periode
    resume = df.groupby(["equipement_id", "periode"]).agg(
        reel=("puissance_w", "sum"),
        attendu=("attendu_w", "sum"),
    ).reset_index()

    # alarmes critiques liees a la puissance ou a la temperature
    alarmes["periode"] = alarmes["horodatage"].dt.floor("2h")
    critiques = alarmes[(alarmes["severite"] == "critical")
                        & alarmes["type_alarme"].isin(["perte_puissance", "sous_tension",
                                                       "surcharge", "surchauffe"])]
    nb_critiques = critiques.groupby(["equipement_id", "periode"]).size().rename("critiques")
    resume = resume.merge(nb_critiques, on=["equipement_id", "periode"], how="left").fillna({"critiques": 0})

    # on additionne les 6 periodes SUIVANTES (12 h dans le futur)
    par_panneau = resume.groupby("equipement_id")
    reel_futur = sum(par_panneau["reel"].shift(-k) for k in range(1, 7))
    attendu_futur = sum(par_panneau["attendu"].shift(-k) for k in range(1, 7))
    critiques_futures = sum(par_panneau["critiques"].shift(-k) for k in range(1, 7))

    perf_future = reel_futur / attendu_futur
    resume["a_risque"] = ((perf_future < 0.65) | (critiques_futures > 0)).astype(int)
    resume = resume[reel_futur.notna()]   # on enleve les periodes sans futur connu

    # on recopie la cible sur chaque mesure
    return df.merge(resume[["equipement_id", "periode", "a_risque"]],
                    on=["equipement_id", "periode"], how="inner")


def charger_jeux():
    """Lit la base, construit features + cible, et renvoie (train, validation, test)."""
    equipements, mesures, orbite, alarmes, maintenances = lire_donnees()
    df = construire_features(equipements, mesures, orbite, alarmes, maintenances)
    df = construire_cible(df, alarmes)

    # decoupage DANS LE TEMPS : on ne melange jamais passe et futur
    train = df[df["horodatage"] < FIN_TRAIN - MARGE]
    validation = df[(df["horodatage"] >= FIN_TRAIN) & (df["horodatage"] < FIN_VALIDATION - MARGE)]
    test = df[df["horodatage"] >= FIN_VALIDATION]
    return train, validation, test


if __name__ == "__main__":
    # petit controle taille des jeux et part a risque
    train, validation, test = charger_jeux()
    for nom, jeu in [("train", train), ("validation", validation), ("test", test)]:
        print(f"{nom:<11} {len(jeu):>7} lignes   part a risque : {jeu['a_risque'].mean():.0%}")
    print("features :", FEATURES)