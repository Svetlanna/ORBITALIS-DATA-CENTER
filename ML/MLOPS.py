"""
ML/MLOPS.py
-----------
Compare automatiquement TOUS les modeles .joblib du dossier model/ et :
  1. evalue chaque modele sur le MEME jeu de test (du 7 au 14 juin)
  2. classe les modeles selon leur cout metier moyen (le plus petit = le meilleur)
  3. identifie les modeles conformes au seuil de qualite
  4. active le meilleur modele conforme dans ML/reglages/modele_actif.json
  5. conserve la configuration existante si aucun modele n'est conforme

En plus, tout est trace dans MLflow :
  - un run "comparaison" avec les scores de test de chaque version
  - l'alias "champion" pose sur la version gagnante dans le Model Registry

Lancer depuis la racine du projet :
    python ML/MLOPS.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# la racine du projet (dossier ORBITALIS) doit etre dans le chemin pour "import config"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import mlflow
import pandas as pd
from mlflow import MlflowClient
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

import config as C          # le fichier config.py a la racine du projet

# --------------------------------------------------------------------------
# REGLAGES
# --------------------------------------------------------------------------
DOSSIER_MODELES = C.RACINE / "model"
FICHIER_ACTIF = C.RACINE / "ML" / "reglages" / "modele_actif.json"

URI_MLFLOW = "sqlite:///" + (C.RACINE / "mlflow.db").as_posix()   # base locale de MLflow
NOM_EXPERIENCE = "orbitalis_risque_panneaux"
NOM_MODELE_REGISTRE = "orbitalis_risque"
ALIAS_PRODUCTION = "champion"

# Couts metier du brief (en euros)
COUT_PANNE_RATEE = 2500       # faux negatif : degradation non anticipee
COUT_INSPECTION_INUTILE = 150 # faux positif
COUT_PANNE_ANTICIPEE = 300    # vrai positif
# vrai negatif : 0 EUR

# SEUIL DE QUALITE un modele est conforme si son cout moyen sur le test
# est inferieur ou egal a cette valeur.
# Repere : "inspecter tous les panneaux tout le temps" coute environ 246 EUR
# par mesure sur le test. Un modele doit faire mieux que cette strategie simple.
SEUIL_COUT_MOYEN = 240.0


# --------------------------------------------------------------------------
# EVALUATION
# --------------------------------------------------------------------------
def calculer_scores(modele, seuil, X, y):
    """Renvoie un dictionnaire de scores pour un modele et un seuil de decision."""
    proba = modele.predict_proba(X)[:, 1]          # probabilite d'etre a risque
    y_predit = (proba >= seuil).astype(int)        # 1 si la proba depasse le seuil
    tn, fp, fn, tp = confusion_matrix(y, y_predit, labels=[0, 1]).ravel()

    cout_total = fn * COUT_PANNE_RATEE + fp * COUT_INSPECTION_INUTILE + tp * COUT_PANNE_ANTICIPEE
    return {
        "cout_moyen": cout_total / len(y),         # en EUR par mesure : notre "erreur moyenne"
        "cout_total": float(cout_total),
        "recall": recall_score(y, y_predit, zero_division=0),
        "precision": precision_score(y, y_predit, zero_division=0),
        "f1": f1_score(y, y_predit, zero_division=0),
        "pannes_ratees": int(fn),
        "inspections_inutiles": int(fp),
    }


def lire_modeles():
    """Charge tous les .joblib du dossier model/. Ignore les fichiers illisibles."""
    modeles = []
    for chemin in sorted(DOSSIER_MODELES.glob("*.joblib")):
        try:
            contenu = joblib.load(chemin)
        except Exception as erreur:
            print(f"  [ignore] {chemin.name} : illisible ({erreur})")
            continue
        if not isinstance(contenu, dict) or "modele" not in contenu:
            print(f"  [ignore] {chemin.name} : format inattendu (pas de cle 'modele')")
            continue
        contenu["fichier"] = chemin.name
        contenu.setdefault("version", chemin.stem)   # l'ancien modele_risque.joblib n'a pas de version
        modeles.append(contenu)
    return modeles


def evaluer_tous(modeles, test):
    """Evalue chaque modele sur le jeu de test et renvoie un tableau classe."""
    lignes = []
    for m in modeles:
        scores = calculer_scores(m["modele"], m.get("seuil", 0.5), test[m["features"]], test["a_risque"])
        lignes.append({
            "version": m["version"],
            "fichier": m["fichier"],
            "nom": m.get("nom", "?"),
            "seuil": m.get("seuil", 0.5),
            "mlflow_version": m.get("mlflow_version"),
            **scores,
        })
    tableau = pd.DataFrame(lignes)
    tableau["conforme"] = tableau["cout_moyen"] <= SEUIL_COUT_MOYEN
    tableau["dans_registre"] = tableau["mlflow_version"].notna()
    # classement : le plus petit cout moyen en premier.
    # En cas d'egalite : le moins de pannes ratees, puis celui qui est dans le registre MLflow.
    tableau = tableau.sort_values(["cout_moyen", "pannes_ratees", "dans_registre"],
                                  ascending=[True, True, False], ignore_index=True)
    tableau.insert(0, "rang", range(1, len(tableau) + 1))
    return tableau


# --------------------------------------------------------------------------
# ACTIVATION
# --------------------------------------------------------------------------
def lire_actif():
    """Renvoie la configuration active, ou None s'il n'y en a pas encore."""
    if not FICHIER_ACTIF.exists():
        return None
    return json.loads(FICHIER_ACTIF.read_text(encoding="utf-8"))


def activer(infos):
    """Ecrit modele_actif.json et pose l'alias 'champion' dans MLflow."""
    infos = dict(infos)
    infos["date_activation"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    FICHIER_ACTIF.parent.mkdir(parents=True, exist_ok=True)
    # on ecrit d'abord un fichier temporaire, puis on le renomme :
    # ainsi, le fichier actif n'est jamais a moitie ecrit
    temporaire = FICHIER_ACTIF.with_suffix(".tmp")
    temporaire.write_text(json.dumps(infos, indent=2, ensure_ascii=False), encoding="utf-8")
    temporaire.replace(FICHIER_ACTIF)

    if infos.get("mlflow_version"):
        client = MlflowClient(tracking_uri=URI_MLFLOW)
        client.set_registered_model_alias(NOM_MODELE_REGISTRE, ALIAS_PRODUCTION,
                                          str(infos["mlflow_version"]))
    return infos


# --------------------------------------------------------------------------
# PROGRAMME PRINCIPAL
# --------------------------------------------------------------------------
def main():
    from Jeux import charger_jeux   # import ici : l'API n'a pas besoin des donnees

    print("1) lecture des modeles dans", DOSSIER_MODELES)
    modeles = lire_modeles()
    if not modeles:
        raise SystemExit("aucun modele .joblib trouve : lancez d'abord python ML/Entrainer_versions.py")

    print("2) evaluation sur le meme jeu de test")
    _, _, test = charger_jeux()
    tableau = evaluer_tous(modeles, test)

    pd.set_option("display.width", 200)
    colonnes = ["rang", "version", "nom", "seuil", "cout_moyen", "recall", "precision",
                "pannes_ratees", "inspections_inutiles", "conforme"]
    print("\n3) classement (seuil de qualite : cout moyen <= "
          f"{SEUIL_COUT_MOYEN} EUR)\n")
    print(tableau[colonnes].round(3).to_string(index=False))

    conformes = tableau[tableau["conforme"]]
    ancien = lire_actif()

    # 4) trace MLflow de la comparaison
    mlflow.set_tracking_uri(URI_MLFLOW)
    mlflow.set_experiment(NOM_EXPERIENCE)
    with mlflow.start_run(run_name="comparaison"):
        mlflow.log_param("seuil_cout_moyen", SEUIL_COUT_MOYEN)
        mlflow.log_param("nb_modeles", len(tableau))
        for _, ligne in tableau.iterrows():
            mlflow.log_metric(f"test_cout_moyen_{ligne['version']}", ligne["cout_moyen"])
            mlflow.log_metric(f"test_recall_{ligne['version']}", ligne["recall"])
        chemin_csv = C.RACINE / "model" / "classement.csv"
        tableau.to_csv(chemin_csv, index=False)
        mlflow.log_artifact(str(chemin_csv))

        # 5) decision
        if conformes.empty:
            mlflow.set_tag("decision", "aucun modele conforme")
            print("\n4) AUCUN modele conforme : la configuration existante est conservee.")
            print("   modele actif :", ancien["version"] if ancien else "aucun")
            return

        meilleur = conformes.iloc[0]
        mlflow.set_tag("decision", f"active {meilleur['version']}")

    infos = {
        "version": meilleur["version"],
        "fichier": meilleur["fichier"],
        "nom": meilleur["nom"],
        "seuil": float(meilleur["seuil"]),
        "cout_moyen_test": round(float(meilleur["cout_moyen"]), 2),
        "recall_test": round(float(meilleur["recall"]), 4),
        "mlflow_modele": NOM_MODELE_REGISTRE,
        "mlflow_version": None if pd.isna(meilleur["mlflow_version"]) else int(meilleur["mlflow_version"]),
        "active_par": "MLOPS.py",
    }
    activer(infos)

    avant = ancien["version"] if ancien else "aucun"
    print(f"\n4) modele active : {infos['version']}  (avant : {avant})")
    print(f"   fichier : {FICHIER_ACTIF}")
    if infos["mlflow_version"]:
        print(f"   MLflow : alias '{ALIAS_PRODUCTION}' -> {NOM_MODELE_REGISTRE} v{infos['mlflow_version']}")


if __name__ == "__main__":
    main()