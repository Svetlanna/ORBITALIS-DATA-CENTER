from pathlib import Path
import json
import sqlite3
import pandas as pd


RACINE = Path(__file__).resolve().parent.parent
RAW = RACINE / "data" / "raw"

ECHANTILLON = None   # mettre 5000 pour tester vite, None pour tout lire

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)




def charger_csv(nom, nrows=None):
    return pd.read_csv(RAW / nom, dtype=str, nrows=nrows)


def charger_json(nom):
    with open(RAW / nom, encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


def charger_sqlite(nom):
    con = sqlite3.connect(RAW / nom)
    noms = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", con)["name"]
    tables = {t: pd.read_sql(f"SELECT * FROM {t}", con) for t in noms}
    con.close()
    return tables



def profiler(df, nom_source, cle=None, seuil_modalites=12):
    print("\n" + "=" * 72)
    print(f"  {nom_source}")
    print("=" * 72)


    lignes, colonnes = df.shape
    print(f"\n volume : {lignes} lignes x {colonnes} colonnes")

    if cle:
        cles = [cle] if isinstance(cle, str) else list(cle)
        doublons_cle = df.duplicated(subset=cles).sum()
        etat = "valide" if doublons_cle == 0 else " invalide "
        print(f"\n  cle ({', '.join(cles)}) : {doublons_cle} doublons "
              f"sur {lignes} lignes -> {etat}")
        if doublons_cle:
            exemples = df.loc[df.duplicated(subset=cles, keep=False), cles]
            print("    exemples :")
            print(exemples.head(6).to_string(index=False))

# value manque
    print("\n  manquents (cellules vides uniquement)")
    manquants = pd.DataFrame({
        "nb": df.isna().sum(),
        "pct": (df.isna().mean() * 100).round(2),
    })
    manquants = manquants[manquants["nb"] > 0]
    print(manquants.to_string() if len(manquants) else "    aucun")

# dublones
    print(f"\n dublons : {df.duplicated().sum()} lignes strictement identiques")

    # --- contenu colonne par colonne
    print("\n contenu")
    for col in df.columns:
        serie = df[col]

        if pd.api.types.is_bool_dtype(serie):
            print(f"  - {col} [booleen] {serie.value_counts(dropna=False).to_dict()}")
            continue

        nombres = pd.to_numeric(serie, errors="coerce")
        non_vides = serie.notna().sum()
        convertibles = nombres.notna().sum()
        est_numerique = non_vides > 0 and convertibles / non_vides > 0.8

        if est_numerique:
            print(f"  - {col} [numerique] min={nombres.min()}  max={nombres.max()}  "
                  f"mediane={nombres.median()}")

            # valeurs non vides devenues NaN apres conversion = texte parasite
            parasites = serie[nombres.isna() & serie.notna()].unique()
            if len(parasites):
                print(f"      /!\\ texte non convertible : {list(parasites)[:5]}")
        else:
            modalites = serie.value_counts(dropna=False)
            if len(modalites) <= seuil_modalites:
                print(f"  - {col} [texte] {len(modalites)} modalites : {modalites.to_dict()}")
            else:
                top = modalites.head(5).to_dict()
                print(f"  - {col} [texte] {len(modalites)} modalites distinctes, top5 : {top}")
    return df




def formats(df, colonne):
    return df[colonne].astype(str).str.replace(r"\d", "9", regex=True).value_counts()


def integrite(libelle, enfant, parent):
    # verifier les cles etrange
    e, p = set(enfant.dropna()), set(parent.dropna())
    orphelins, muets = sorted(e - p), sorted(p - e)
    print(f"\n  {libelle}")
    print(f"    orphelins (pointent vers rien)  : {len(orphelins)} {orphelins[:8]}")
    print(f"    jamais references               : {len(muets)} {muets[:8]}")


def profiler_colonnes(sources):
    """rend un tableau une ligne par colonne de chaque source"""
    lignes = []
    for nom, df in sources.items():
        for col in df.columns:
            s = df[col]
            manquants = int(s.isna().sum())
            lignes.append({
                "source": nom,
                "colonne": col,
                "type_lu": str(s.dtype),
                "manquants": manquants,
                "pct_manquants": round(100 * manquants / len(df), 2) if len(df) else 0.0,
                "distincts": int(s.nunique(dropna=True)),
            })
    return pd.DataFrame(lignes)


def profil_vers_markdown(profil, seulement_problemes=False):
    """rend le tableau en markdown collable dans la synthese"""
    p = profil[profil["manquants"] > 0] if seulement_problemes else profil
    entete = "| source | colonne | type lu | manquants | % | distincts |"
    trait = "|---|---|---|---|---|---|"
    corps = [
        f"| {r.source} | {r.colonne} | `{r.type_lu}` | {r.manquants} | {r.pct_manquants} | {r.distincts} |"
        for r in p.itertuples()
    ]
    return "\n".join([entete, trait] + corps)

if __name__ == "__main__":
    sites       = charger_csv("sites.csv")
    equipements = charger_csv("equipements.csv")
    maintenance = charger_csv("maintenance.csv")
    orbite      = charger_csv("orbite.csv")
    telemetrie  = charger_csv("telemetrie.csv", nrows=ECHANTILLON)
    alarmes     = charger_json("alarmes.json")
    catalogue   = charger_sqlite("catalogue.db")

    profiler(sites,       "sites.csv",       cle="site_id")
    profiler(equipements, "equipements.csv", cle="equipement_id")
    profiler(maintenance, "maintenance.csv", cle="maintenance_id")
    profiler(orbite,      "orbite.csv",      cle=["timestamp", "site_id"])
    profiler(telemetrie,  "telemetrie.csv",  cle=["timestamp", "equipement_id"])
    profiler(alarmes,     "alarmes.json",    cle="alarme_id")
    for nom, table in catalogue.items():
        profiler(table, f"catalogue.db :: {nom}")

    # --- formats de dates
    print("\n" + "=" * 72)
    print("  FORMATS DE DATES")
    print("=" * 72)
    for df, col, libelle in [
        (equipements, "date_installation", "equipements.date_installation"),
        (maintenance, "date_debut",        "maintenance.date_debut"),
        (alarmes,     "timestamp",         "alarmes.timestamp"),
        (orbite,      "timestamp",         "orbite.timestamp"),
        (telemetrie,  "timestamp",         "telemetrie.timestamp"),
    ]:
        print(f"\n{libelle} :")
        print(formats(df, col).head(8).to_string())

    # --- Integrite referentielle
    print("\n" + "=" * 72)
    print("  INTEGRITE REFERENTIELLE")
    print("=" * 72)
    integrite("equipements.site_id       -> sites",             equipements["site_id"],       sites["site_id"])
    integrite("orbite.site_id            -> sites",             orbite["site_id"],            sites["site_id"])
    integrite("telemetrie.equipement_id  -> equipements",       telemetrie["equipement_id"],  equipements["equipement_id"])
    integrite("alarmes.equipement_id     -> equipements",       alarmes["equipement_id"],     equipements["equipement_id"])
    integrite("maintenance.equipement_id -> equipements",       maintenance["equipement_id"], equipements["equipement_id"])
    integrite("equipements.modele        -> catalogue.modeles", equipements["modele"],        catalogue["modeles"]["modele_id"])