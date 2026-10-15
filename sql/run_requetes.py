import sqlite3
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

RACINE      = Path(__file__).resolve().parents[1]
BASE        = RACINE / "data" / "db" / "orbitalis_etoile.db"
FICHIER_SQL = RACINE / "sql" / "analyse.sql"
SORTIE_MD   = RACINE / "docs" / "resultats_requetes.md"

MARQUEUR = "-- @"
# au-dela, le fichier md deviendrait illisible (Q1 renvoie 1080 lignes)
MAX_LIGNES = 30


#  lecture du fichier sql

def lire_requetes(chemin):
    requetes = []
    titre, lignes = None, []

    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.startswith(MARQUEUR):
            if titre is not None:
                requetes.append((titre, "\n".join(lignes).strip()))
            titre, lignes = ligne[len(MARQUEUR):].strip(), []
        elif titre is not None:
            lignes.append(ligne)

    if titre is not None:
        requetes.append((titre, "\n".join(lignes).strip()))
    return requetes


#  execution

def executer(con, requete):
    """Renvoie (DataFrame ou None, duree en secondes)."""
    debut = time.perf_counter()
    curseur = con.execute(requete)
    # un CREATE INDEX ou un ANALYZE ne renvoie pas de colonnes
    if curseur.description is None:
        con.commit()
        return None, time.perf_counter() - debut
    colonnes = [description[0] for description in curseur.description]
    # dtype=object garde les valeurs telles que sqlite les renvoie (72510 reste 72510, pas 72510.0)
    df = pd.DataFrame(curseur.fetchall(), columns=colonnes, dtype=object)
    return df, time.perf_counter() - debut





def cellule(valeur):
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return ""

    return str(valeur).replace("|", "\\|")


def tableau_markdown(df):
    lignes = ["| " + " | ".join(df.columns) + " |",
              "| " + " | ".join("---" for _ in df.columns) + " |"]
    for rangee in df.itertuples(index=False, name=None):
        lignes.append("| " + " | ".join(cellule(v) for v in rangee) + " |")
    return "\n".join(lignes)


def section_markdown(titre, requete, df, duree):
    morceaux = [f"## {titre}", "", "```sql", requete, "```", ""]

    if df is None:
        morceaux.append(f"_Requete executee sans resultat a afficher ({duree:.2f} s)._")
    elif df.empty:
        morceaux.append(f"_Aucune ligne ({duree:.2f} s)._")
    else:
        morceaux.append(f"**{len(df)} ligne(s)** - {duree:.2f} s")
        morceaux.append("")
        morceaux.append(tableau_markdown(df.head(MAX_LIGNES)))
        if len(df) > MAX_LIGNES:
            morceaux.append("")
            morceaux.append(f"_... {MAX_LIGNES} premieres lignes affichees sur {len(df)}._")

    morceaux.append("")
    return "\n".join(morceaux)





def main():
    if not BASE.exists():
        raise SystemExit(f"base introuvable : {BASE}\nlancez d'abord python etl/load.py")

    requetes = lire_requetes(FICHIER_SQL)
    print(f"{len(requetes)} requetes trouvees dans {FICHIER_SQL.name}\n")

    sections = [f"# Resultats des requetes ORBITALIS", "",
                f"- base : `{BASE.relative_to(RACINE)}`",
                f"- fichier : `{FICHIER_SQL.relative_to(RACINE)}`",
                f"- genere le {datetime.now():%Y-%m-%d %H:%M}", ""]

    con = sqlite3.connect(BASE)
    for titre, requete in requetes:
        print("=" * 70)
        print(titre)
        print("=" * 70)
        try:
            df, duree = executer(con, requete)
        except sqlite3.Error as erreur:
            # une requete fausse ne doit pas empecher les autres de tourner
            print(f"  ERREUR : {erreur}\n")
            sections.append(f"## {titre}\n\n```sql\n{requete}\n```\n\n**ERREUR** : `{erreur}`\n")
            continue

        if df is None:
            print(f"  executee ({duree:.2f} s)\n")
        else:
            with pd.option_context("display.max_columns", None, "display.width", 200):
                print(df.head(MAX_LIGNES).to_string(index=False))
            print(f"  -> {len(df)} ligne(s) en {duree:.2f} s\n")
        sections.append(section_markdown(titre, requete, df, duree))
    con.close()

    SORTIE_MD.parent.mkdir(parents=True, exist_ok=True)
    SORTIE_MD.write_text("\n".join(sections), encoding="utf-8")
    print(f"resultats sauvegardes dans {SORTIE_MD}")


if __name__ == "__main__":
    main()