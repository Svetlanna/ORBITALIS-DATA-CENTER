# 
# ML/Entrainer_versions.py
# ------------------------
# Entraine PLUSIEURS versions candidates du modele de risque, puis pour chacune
#   1. la sauvegarde dans model/modele_risque_vN.joblib  (meme format que Train.py)
#   2. l'enregistre dans MLflow
#        - un "run"  = une experience (parametres + scores + modele)
#        - une "version" dans le Model Registry, sous le nom "orbitalis_risque"
#
# Lancer depuis la racine du projet :
#     python ML/Entrainer_versions.py
#

import sys
from pathlib import Path

# la racine du projet (dossier ORBITALIS) doit etre dans le chemin pour "import config"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from Jeux import FIN_TRAIN, charger_jeux
from Preparation import FEATURES
from MLOPS import (DOSSIER_MODELES, NOM_EXPERIENCE, NOM_MODELE_REGISTRE,
                   URI_MLFLOW, calculer_scores)


def candidats():
    """La liste des versions a essayer : (version, nom, pipeline, seuil de decision)."""
    def logistique(c):
        return make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(C=c, max_iter=1000, class_weight="balanced"),
        )

    def foret():
        return make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(n_estimators=200, min_samples_leaf=20,
                                   class_weight="balanced", random_state=42, n_jobs=-1),
        )

    # Le SEUIL : au-dessus de cette probabilite, on declare "a risque".
    # Un seuil plus bas = plus d'alertes = moins de pannes ratees (mais plus d'inspections).
    return [
        ("v1", "regression_logistique", logistique(1.0), 0.5),
        ("v2", "regression_logistique", logistique(1.0), 0.3),
        ("v3", "random_forest", foret(), 0.5),
        ("v4", "random_forest", foret(), 0.3),
    ]


def main():
    # 1) dire a MLflow OU ranger les informations (un fichier mlflow.db a la racine)
    mlflow.set_tracking_uri(URI_MLFLOW)
    mlflow.set_experiment(NOM_EXPERIENCE)   # cree l'experience si elle n'existe pas

    train, validation, _ = charger_jeux()   # le test est garde pour MLOPS.py
    X_train, y_train = train[FEATURES], train["a_risque"]
    X_val, y_val = validation[FEATURES], validation["a_risque"]

    DOSSIER_MODELES.mkdir(exist_ok=True)

    for version, nom, modele, seuil in candidats():
        print(f"\n=== {version} : {nom}, seuil {seuil} ===")
        modele.fit(X_train, y_train)

        # 2) un "run" MLflow = une boite qui garde tout ce qui concerne CET entrainement
        with mlflow.start_run(run_name=f"{version}_{nom}_seuil{seuil}") as run:
            # les reglages (parametres)
            mlflow.log_param("version", version)
            mlflow.log_param("algorithme", nom)
            mlflow.log_param("seuil", seuil)
            mlflow.log_param("fin_train", str(FIN_TRAIN))
            mlflow.log_param("nb_lignes_train", len(X_train))

            # les scores sur la VALIDATION (prefixe val_)
            scores = calculer_scores(modele, seuil, X_val, y_val)
            for cle, valeur in scores.items():
                mlflow.log_metric(f"val_{cle}", valeur)
            print(f"  validation : cout moyen {scores['cout_moyen']:.1f} EUR, "
                  f"recall {scores['recall']:.3f}, f1 {scores['f1']:.3f}")

            # 3) le modele lui-meme + enregistrement dans le Model Registry
            #    registered_model_name => MLflow cree "orbitalis_risque" version 1, 2, 3...
            info = mlflow.sklearn.log_model(
                sk_model=modele,
                name="modele",
                registered_model_name=NOM_MODELE_REGISTRE,
                input_example=X_val.head(3),
                # format de sauvegarde classique, compatible avec toutes les versions de MLflow
                serialization_format="cloudpickle",
            )
            version_mlflow = info.registered_model_version
            mlflow.set_tag("fichier_joblib", f"modele_risque_{version}.joblib")

        # 4) le fichier .joblib local (meme format que Train.py + infos MLflow)
        chemin = DOSSIER_MODELES / f"modele_risque_{version}.joblib"
        joblib.dump(
            {
                "modele": modele,
                "nom": nom,
                "version": version,
                "features": FEATURES,
                "seuil": seuil,
                "fin_train": str(FIN_TRAIN),
                "mlflow_run_id": run.info.run_id,
                "mlflow_version": version_mlflow,
            },
            chemin,
        )
        print(f"  sauvegarde : {chemin.name}  (registre MLflow : {NOM_MODELE_REGISTRE} v{version_mlflow})")

    print(f"\nTermine. Pour voir les runs : mlflow ui --backend-store-uri {URI_MLFLOW}")


if __name__ == "__main__":
    main()