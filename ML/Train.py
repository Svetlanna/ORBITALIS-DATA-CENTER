from Preparation import FEATURES, construire_features, lire_donnees
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import joblib

import config as C
# ----------------

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score


# ----------------
from sklearn.metrics import confusion_matrix
equipements, mesures, orbite, alarmes, maintenances = lire_donnees()
df = construire_features(equipements, mesures, orbite, alarmes, maintenances)



logistique = make_pipeline(
    SimpleImputer(strategy="median"),
    StandardScaler(),
    LogisticRegression(max_iter=1000, class_weight="balanced"),
)

foret = make_pipeline(
    SimpleImputer(strategy="median"),
    RandomForestClassifier(n_estimators=200, min_samples_leaf=20,
                           class_weight="balanced", random_state=42, n_jobs=-1),
)


#1  cible y

#chaque mesure appartient a une periode orbitale de 2 h
df["periode"] = df["horodatage"].dt.floor("2h")
df["attendu_w"] = (df["puissance_nominale_w"] * df["rayonnement"]).where(df["puissance_w"].notna())

#un resume par panneau et par periode
resume = df.groupby(["equipement_id", "periode"]).agg(
    reel=("puissance_w", "sum"),
    attendu=("attendu_w", "sum"),
).reset_index()

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
resume = resume[reel_futur.notna()]

#on recopie la cible sur chaque mesure
df = df.merge(resume[["equipement_id", "periode", "a_risque"]],
              on=["equipement_id", "periode"], how="inner")

X = df[FEATURES]
y = df["a_risque"]




# decoupage dans le temps


FIN_TRAIN = pd.Timestamp("2025-05-31")
FIN_VALIDATION = pd.Timestamp("2025-06-07")
MARGE = pd.Timedelta("12h")

train = df[df["horodatage"] < FIN_TRAIN - MARGE]
validation = df[(df["horodatage"] >= FIN_TRAIN) & (df["horodatage"] < FIN_VALIDATION - MARGE)]
test = df[df["horodatage"] >= FIN_VALIDATION]

X_train, y_train = train[FEATURES], train["a_risque"]
X_val, y_val = validation[FEATURES], validation["a_risque"]
X_test, y_test = test[FEATURES], test["a_risque"]


logistique.fit(X_train, y_train)     # il apprend les poids
logistique.predict(X_val)            # il répond 0 ou 1




#  entrainer les deux model
logistique.fit(X_train, y_train)
foret.fit(X_train, y_train)

# ---------- SCORES ----------
for nom, modele in [("REGRESSION LOGISTIQUE", logistique), ("RANDOM FOREST", foret)]:
    y_predit = modele.predict(X_val)
    proba = modele.predict_proba(X_val)[:, 1]
    tn, fp, fn, tp = confusion_matrix(y_val, y_predit).ravel()

    print(f"\n{nom} (validation, seuil 0.5)")
    print(f"  accuracy  : {accuracy_score(y_val, y_predit)}")
    print(f"  precision : {precision_score(y_val, y_predit)}")
    print(f"  recall    : {recall_score(y_val, y_predit)}")
    print(f"  f1        : {f1_score(y_val, y_predit)}")
    print(f"  roc auc   : {roc_auc_score(y_val, proba)}")


    print(f"  bien vu normal      : {tn}")
    print(f"  inspection inutile  : {fp}")
    print(f"  degradation ratee   : {fn}")
    print(f"  degradation anticipee : {tp}")


# -----------------------------------------------------------------------
pd.set_option("display.max_columns", None)   # montrer toutes les colonnes
pd.set_option("display.width", 200)

colonnes = ["equipement_id", "horodatage"] + FEATURES + ["a_risque"]

print("\n===== TRAIN =====")
print(train[colonnes].head())
print("\n===== VALIDATION =====")
print(validation[colonnes].head())
print("\n===== TEST =====")
print(test[colonnes].head())

# ---------- AFFICHER LES PREDICTIONS ----------
resultat = validation[["equipement_id", "horodatage", "puissance_w"]].copy()
resultat["vrai"] = y_val
resultat["proba_logistique"] = logistique.predict_proba(X_val)[:, 1].round(2)
resultat["predit_logistique"] = logistique.predict(X_val)
resultat["proba_foret"] = foret.predict_proba(X_val)[:, 1].round(2)
resultat["predit_foret"] = foret.predict(X_val)

print("\n===== PREDICTIONS (validation) =====")
print(resultat.head(10))

print("\n===== ERREURS : degradations ratees par la foret =====")
print(resultat[(resultat["vrai"] == 1) & (resultat["predit_foret"] == 0)].head(10))





# ---------- GRAPHIQUE POUR UN PANNEAU ----------
DOSSIER_GRAPHIQUES = C.RACINE / "graphique"
DOSSIER_GRAPHIQUES.mkdir(exist_ok=True)

jeux = {"train": train, "validation": validation, "test": test}
couleurs = {"train": "tab:blue", "validation": "tab:orange", "test": "tab:green"}

morceaux = []
for nom_jeu, partie in jeux.items():
    morceau = partie[["equipement_id", "horodatage", "periode", "puissance_moyenne_24h", "a_risque"]].copy()
    morceau["jeu"] = nom_jeu
    morceau["proba_logistique"] = logistique.predict_proba(partie[FEATURES])[:, 1]
    morceau["proba_foret"] = foret.predict_proba(partie[FEATURES])[:, 1]
    morceaux.append(morceau)
resultat = pd.concat(morceaux)

# ---------- GRAPHIQUE 1 : un panneau, une valeur par periode de 2 h ----------
PANNEAU = "EQ-037"

p = (resultat[resultat["equipement_id"] == PANNEAU]
     .groupby(["periode", "jeu"], as_index=False)
     .agg(puissance=("puissance_moyenne_24h", "mean"),
          vrai=("a_risque", "max"),
          logistique=("proba_logistique", "mean"),
          foret=("proba_foret", "mean")))

fig, (haut, bas) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)

for nom_jeu, partie in p.groupby("jeu"):
    debut, fin = partie["periode"].min(), partie["periode"].max()
    for axe in (haut, bas):
        axe.axvspan(debut, fin, color=couleurs[nom_jeu], alpha=0.12)
    haut.text(debut, p["puissance"].max(), " " + nom_jeu.upper(),
              color=couleurs[nom_jeu], fontweight="bold", va="top")

haut.plot(p["periode"], p["puissance"], color="black")
haut.set_ylabel("puissance moyenne 24h (W)")
haut.set_title(f"{PANNEAU} : la production baisse avec le temps")

bas.fill_between(p["periode"], 0, p["vrai"], step="post", color="grey", alpha=0.35,
                 label="vraiment a risque")
bas.plot(p["periode"], p["logistique"], color="tab:red", label="proba logistique")
bas.plot(p["periode"], p["foret"], color="tab:purple", label="proba foret")
bas.axhline(0.5, color="black", linestyle="--", linewidth=1, label="seuil 0.5")
bas.set_ylim(-0.02, 1.02)
bas.set_ylabel("probabilite de risque")
bas.set_title("zone grise = vrai risque | courbe au-dessus de 0.5 = le modele alerte")
bas.legend(loc="lower left")

plt.tight_layout()
plt.savefig(DOSSIER_GRAPHIQUES / f"predictions_{PANNEAU}.png")



# ---------- GRAPHIQUE 2 : scores par jeu, pour les deux model ----------
lignes = []
for nom_jeu, partie in jeux.items():
    for nom_modele, modele in [("logistique", logistique), ("foret", foret)]:
        y_vrai = partie["a_risque"]
        y_predit = modele.predict(partie[FEATURES])
        lignes.append({"jeu": nom_jeu, "modele": nom_modele,
                       "precision": precision_score(y_vrai, y_predit),
                       "recall": recall_score(y_vrai, y_predit),
                       "f1": f1_score(y_vrai, y_predit)})
scores = pd.DataFrame(lignes)
print(scores.round(3).to_string(index=False))

fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
for axe, score in zip(axes, ["precision", "recall", "f1"]):
    tableau = scores.pivot(index="jeu", columns="modele", values=score).loc[list(jeux)]
    tableau.plot.bar(ax=axe, color={"logistique": "tab:red", "foret": "tab:purple"}, rot=0, legend=False)
    axe.set_title(score)
    axe.set_ylim(0, 1)
    axe.set_xlabel("")
plt.suptitle("scores des deux model sur train, validation et test (seuil 0.5)")
fig.legend(*axes[0].get_legend_handles_labels(), loc="upper right", ncol=2)
plt.tight_layout()
plt.savefig(DOSSIER_GRAPHIQUES / "scores_par_jeu.png")






# ---------- SAUVEGARDER LE MODELE ----------
DOSSIER_MODELES = C.RACINE / "model"
DOSSIER_MODELES.mkdir(exist_ok=True)

joblib.dump(
    {
        "modele": logistique,
        "nom": "regression_logistique",
        "features": FEATURES,
        "seuil": 0.5,                      # a remplacer par le seuil de l'etape 4
        "fin_train": str(FIN_TRAIN),
    },
    DOSSIER_MODELES / "modele_risque.joblib",
)
print(f"\nmodele sauvegarde dans {DOSSIER_MODELES / 'modele_risque.joblib'}")