import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# on ajoute le dossier ML/ au chemin pour pouvoir importer MLOPS.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ML"))

from MLOPS import activer, lire_actif, lire_modeles   # noqa: E402  (import apres sys.path)

app = FastAPI(title="ORBITALIS - gestion du modele de risque")


class DemandeActivation(BaseModel):
    """Le corps (body) attendu par POST /modele/activer."""
    version: str


@app.get("/modele/actif")
def modele_actif():
    actif = lire_actif()
    if actif is None:
        raise HTTPException(status_code=404, detail="aucun modele actif : lancez python ML/MLOPS.py")
    return actif


@app.get("/modeles")
def liste_modeles():
    return [
        {"version": m["version"], "fichier": m["fichier"], "nom": m.get("nom"),
         "seuil": m.get("seuil"), "mlflow_version": m.get("mlflow_version")}
        for m in lire_modeles()
    ]


@app.post("/modele/activer")
def activer_modele(demande: DemandeActivation):
    # on cherche la version demandee parmi les fichiers .joblib
    trouves = [m for m in lire_modeles() if m["version"] == demande.version]
    if not trouves:
        disponibles = [m["version"] for m in lire_modeles()]
        raise HTTPException(status_code=404,
                            detail=f"version '{demande.version}' introuvable. Disponibles : {disponibles}")
    m = trouves[0]

    infos = activer({
        "version": m["version"],
        "fichier": m["fichier"],
        "nom": m.get("nom"),
        "seuil": m.get("seuil", 0.5),
        "mlflow_modele": "orbitalis_risque",
        "mlflow_version": m.get("mlflow_version"),
        "active_par": "POST /modele/activer",   # activation manuelle (ex. retour arriere)
    })
    return {"message": f"modele {m['version']} active", "actif": infos}