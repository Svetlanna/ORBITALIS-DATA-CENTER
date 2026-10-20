#
# ML/Prediction.py
# ----------------
# Calcule le score de risque des panneaux avec le modele ACTIF.
# Le script ne choisit jamais lui-meme le modele : il lit ML/reglages/modele_actif.json.
# Changer de version = lancer MLOPS.py ou POST /modele/activer, sans toucher a ce fichier.
#
# Lancer depuis la racine du projet :
#     python ML/Prediction.py

import joblib

from MLOPS import DOSSIER_MODELES, FICHIER_ACTIF, lire_actif   # MLOPS ajoute la racine au sys.path
from Jeux import charger_jeux


def charger_modele_actif():
    actif = lire_actif()
    if actif is None:
        raise SystemExit(f"{FICHIER_ACTIF} introuvable : lancez d'abord python ML/MLOPS.py")
    paquet = joblib.load(DOSSIER_MODELES / actif["fichier"])
    return actif, paquet


def main():
    actif, paquet = charger_modele_actif()
    print(f"modele actif : {actif['version']} ({paquet['nom']}, seuil {paquet['seuil']})")

    # pour l'exemple on predit sur la derniere mesure de chaque panneau du jeu de test
    _, _, test = charger_jeux()
    dernieres = test.sort_values("horodatage").groupby("equipement_id").tail(1)

    proba = paquet["modele"].predict_proba(dernieres[paquet["features"]])[:, 1]
    resultat = dernieres[["equipement_id", "horodatage"]].copy()
    resultat["proba_risque"] = proba.round(3)
    resultat["alerte"] = (proba >= paquet["seuil"]).astype(int)   # 1 = planifier une inspection

    print(resultat.sort_values("proba_risque", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    main()