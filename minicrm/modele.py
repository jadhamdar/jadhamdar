# -*- coding: utf-8 -*-
"""MiniCRM — couche d'accès aux données (SQLite).

Module indépendant de l'interface graphique : il peut être importé et testé
sans tkinter. Les données vivent dans un fichier ``minicrm.db`` placé à côté
de l'exécutable (ou du script), ce qui rend l'application portable.
"""

import csv
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta

APP_NAME = "MiniCRM"
DB_NAME = "minicrm.db"

TYPES_PISTE = ["CDI", "Freelance", "Autre"]
STATUTS_PISTE = ["Nouveau", "En cours", "Relancé", "Gagné", "Perdu"]
STATUTS_ACTIFS = ["Nouveau", "En cours", "Relancé"]
JOURS_RELANCE_DEFAUT = 7

CHAMPS_PISTE = ["nom", "societe", "type", "statut", "source", "email",
                "telephone", "prochaine_relance", "notes"]
CHAMPS_CONTACT = ["nom", "societe", "fonction", "email", "telephone",
                  "piste_id", "notes"]

SOURCES_PAR_DEFAUT = ["CollectiveWork", "mon-consultant-indépendant", "Autre"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS pistes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    societe TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'CDI',
    statut TEXT NOT NULL DEFAULT 'Nouveau',
    source TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    telephone TEXT NOT NULL DEFAULT '',
    prochaine_relance TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    cree_le TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    societe TEXT NOT NULL DEFAULT '',
    fonction TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    telephone TEXT NOT NULL DEFAULT '',
    piste_id INTEGER,
    notes TEXT NOT NULL DEFAULT '',
    cree_le TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (piste_id) REFERENCES pistes(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_pistes_relance ON pistes(prochaine_relance);
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE
);
"""


def db_path():
    """Chemin du fichier SQLite : à côté de l'exécutable si packagé, du script sinon."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, DB_NAME)


def parse_date(texte):
    """Convertit 'AAAA-MM-JJ' en date. Retourne None si vide, lève ValueError si invalide."""
    texte = (texte or "").strip()
    if not texte:
        return None
    return datetime.strptime(texte, "%Y-%m-%d").date()


def valider_piste(d):
    """Normalise et valide un dictionnaire de piste. Lève ValueError si invalide."""
    out = {c: str(d.get(c) or "").strip() for c in CHAMPS_PISTE}
    if not out["nom"]:
        raise ValueError("Le nom de la piste est obligatoire.")
    if not out["type"]:
        out["type"] = TYPES_PISTE[0]
    if not out["statut"]:
        out["statut"] = STATUTS_PISTE[0]
    if out["type"] not in TYPES_PISTE:
        raise ValueError("Type invalide : %r (attendu : %s)." % (out["type"], " / ".join(TYPES_PISTE)))
    if out["statut"] not in STATUTS_PISTE:
        raise ValueError("Statut invalide : %r (attendu : %s)." % (out["statut"], " / ".join(STATUTS_PISTE)))
    if out["prochaine_relance"]:
        try:
            parse_date(out["prochaine_relance"])
        except ValueError:
            raise ValueError("Date de relance invalide (format attendu : AAAA-MM-JJ).")
    return out


def valider_contact(d):
    """Normalise et valide un dictionnaire de contact. Lève ValueError si invalide."""
    out = {c: str(d.get(c) or "").strip() for c in CHAMPS_CONTACT}
    if not out["nom"]:
        raise ValueError("Le nom du contact est obligatoire.")
    pid = out["piste_id"]
    out["piste_id"] = int(pid) if pid else None
    return out


class Database:
    """Accès SQLite : pistes, contacts, relances, statistiques, export CSV."""

    def __init__(self, path=None):
        self.path = path or db_path()
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._seed_sources()
        self.conn.commit()

    def _seed_sources(self):
        """Alimente le référentiel des sources s'il est vide (premier lancement)."""
        if self.conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == 0:
            for nom in SOURCES_PAR_DEFAUT:
                self.conn.execute("INSERT OR IGNORE INTO sources (nom) VALUES (?)", (nom,))

    def fermer(self):
        self.conn.close()

    # ---------------- référentiel des sources ----------------

    def sources(self):
        """Sources du référentiel, avec le nombre de pistes qui les utilisent."""
        sql = ("SELECT s.id, s.nom, COUNT(p.id) AS nb_pistes FROM sources s"
               " LEFT JOIN pistes p ON p.source = s.nom"
               " GROUP BY s.id ORDER BY s.nom COLLATE NOCASE")
        return self.conn.execute(sql).fetchall()

    def _valider_nom_source(self, nom):
        nom = (nom or "").strip()
        if not nom:
            raise ValueError("Le nom de la source est obligatoire.")
        return nom

    def ajouter_source(self, nom):
        nom = self._valider_nom_source(nom)
        try:
            cur = self.conn.execute("INSERT INTO sources (nom) VALUES (?)", (nom,))
        except sqlite3.IntegrityError:
            raise ValueError("La source « %s » existe déjà." % nom)
        self.conn.commit()
        return cur.lastrowid

    def renommer_source(self, sid, nouveau_nom):
        nouveau_nom = self._valider_nom_source(nouveau_nom)
        try:
            self.conn.execute("UPDATE sources SET nom=? WHERE id=?", (nouveau_nom, sid))
        except sqlite3.IntegrityError:
            raise ValueError("La source « %s » existe déjà." % nouveau_nom)
        self.conn.commit()

    def supprimer_source(self, sid):
        """Supprime une source du référentiel.

        Retourne le nombre de pistes qui l'utilisaient ; ces pistes
        conservent simplement leur valeur texte (pas de perte de données).
        """
        row = self.conn.execute("SELECT nom FROM sources WHERE id=?", (sid,)).fetchone()
        if row is None:
            return 0
        nb = self.conn.execute("SELECT COUNT(*) FROM pistes WHERE source=?",
                               (row["nom"],)).fetchone()[0]
        self.conn.execute("DELETE FROM sources WHERE id=?", (sid,))
        self.conn.commit()
        return nb

    # ---------------- pistes ----------------

    def ajouter_piste(self, d):
        d = valider_piste(d)
        cur = self.conn.execute(
            "INSERT INTO pistes (nom, societe, type, statut, source, email, telephone,"
            " prochaine_relance, notes, cree_le) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (d["nom"], d["societe"], d["type"], d["statut"], d["source"], d["email"],
             d["telephone"], d["prochaine_relance"], d["notes"], date.today().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def modifier_piste(self, pid, d):
        d = valider_piste(d)
        self.conn.execute(
            "UPDATE pistes SET nom=?, societe=?, type=?, statut=?, source=?, email=?,"
            " telephone=?, prochaine_relance=?, notes=? WHERE id=?",
            (d["nom"], d["societe"], d["type"], d["statut"], d["source"], d["email"],
             d["telephone"], d["prochaine_relance"], d["notes"], pid),
        )
        self.conn.commit()

    def supprimer_piste(self, pid):
        self.conn.execute("UPDATE contacts SET piste_id=NULL WHERE piste_id=?", (pid,))
        self.conn.execute("DELETE FROM pistes WHERE id=?", (pid,))
        self.conn.commit()

    def get_piste(self, pid):
        return self.conn.execute("SELECT * FROM pistes WHERE id=?", (pid,)).fetchone()

    def pistes(self, recherche="", type_filtre="Tous", statut_filtre="Tous"):
        sql = "SELECT * FROM pistes WHERE 1=1"
        params = []
        recherche = (recherche or "").strip()
        if recherche:
            sql += " AND (nom LIKE ? OR societe LIKE ? OR email LIKE ? OR source LIKE ? OR notes LIKE ?)"
            like = "%" + recherche + "%"
            params.extend([like] * 5)
        if type_filtre and type_filtre != "Tous":
            sql += " AND type=?"
            params.append(type_filtre)
        if statut_filtre and statut_filtre != "Tous":
            sql += " AND statut=?"
            params.append(statut_filtre)
        sql += " ORDER BY CASE WHEN prochaine_relance='' THEN 1 ELSE 0 END, prochaine_relance, id"
        return self.conn.execute(sql, params).fetchall()

    # ---------------- relances ----------------

    def relances(self):
        """Pistes actives ayant une date de relance, triées par date croissante."""
        sql = ("SELECT * FROM pistes WHERE prochaine_relance <> '' AND statut IN (?,?,?)"
               " ORDER BY prochaine_relance, id")
        return self.conn.execute(sql, STATUTS_ACTIFS).fetchall()

    def relance_effectuee(self, pid, jours=JOURS_RELANCE_DEFAUT):
        """Marque la relance comme faite : décale la date et passe 'Nouveau' -> 'Relancé'."""
        nouvelle = (date.today() + timedelta(days=jours)).isoformat()
        self.conn.execute(
            "UPDATE pistes SET prochaine_relance=?,"
            " statut=CASE WHEN statut='Nouveau' THEN 'Relancé' ELSE statut END WHERE id=?",
            (nouvelle, pid),
        )
        self.conn.commit()

    def definir_relance(self, pid, date_iso):
        parse_date(date_iso)
        self.conn.execute("UPDATE pistes SET prochaine_relance=? WHERE id=?",
                          (date_iso.strip(), pid))
        self.conn.commit()

    # ---------------- contacts ----------------

    def ajouter_contact(self, d):
        d = valider_contact(d)
        cur = self.conn.execute(
            "INSERT INTO contacts (nom, societe, fonction, email, telephone, piste_id, notes, cree_le)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (d["nom"], d["societe"], d["fonction"], d["email"], d["telephone"],
             d["piste_id"], d["notes"], date.today().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def modifier_contact(self, cid, d):
        d = valider_contact(d)
        self.conn.execute(
            "UPDATE contacts SET nom=?, societe=?, fonction=?, email=?, telephone=?, piste_id=?, notes=?"
            " WHERE id=?",
            (d["nom"], d["societe"], d["fonction"], d["email"], d["telephone"],
             d["piste_id"], d["notes"], cid),
        )
        self.conn.commit()

    def supprimer_contact(self, cid):
        self.conn.execute("DELETE FROM contacts WHERE id=?", (cid,))
        self.conn.commit()

    def get_contact(self, cid):
        return self.conn.execute(
            "SELECT c.*, p.nom AS piste_nom FROM contacts c LEFT JOIN pistes p ON p.id=c.piste_id"
            " WHERE c.id=?", (cid,)).fetchone()

    def contacts(self, recherche=""):
        sql = ("SELECT c.*, p.nom AS piste_nom FROM contacts c"
               " LEFT JOIN pistes p ON p.id = c.piste_id WHERE 1=1")
        params = []
        recherche = (recherche or "").strip()
        if recherche:
            sql += " AND (c.nom LIKE ? OR c.societe LIKE ? OR c.email LIKE ? OR c.notes LIKE ? OR p.nom LIKE ?)"
            like = "%" + recherche + "%"
            params.extend([like] * 5)
        sql += " ORDER BY c.nom"
        return self.conn.execute(sql, params).fetchall()

    # ---------------- statistiques & export ----------------

    def stats(self):
        aujourdhui = date.today().isoformat()

        def compte(sql, params=()):
            return self.conn.execute(sql, params).fetchone()[0]

        actifs = tuple(STATUTS_ACTIFS)
        return {
            "pistes_total": compte("SELECT COUNT(*) FROM pistes"),
            "contacts_total": compte("SELECT COUNT(*) FROM contacts"),
            "relance_retard": compte(
                "SELECT COUNT(*) FROM pistes WHERE prochaine_relance <> '' AND prochaine_relance < ?"
                " AND statut IN (?,?,?)", (aujourdhui, *actifs)),
            "relance_aujourdhui": compte(
                "SELECT COUNT(*) FROM pistes WHERE prochaine_relance = ? AND statut IN (?,?,?)",
                (aujourdhui, *actifs)),
            "par_type": {t: compte("SELECT COUNT(*) FROM pistes WHERE type=?", (t,)) for t in TYPES_PISTE},
            "par_statut": {s: compte("SELECT COUNT(*) FROM pistes WHERE statut=?", (s,)) for s in STATUTS_PISTE},
        }

    def export_csv(self, table, chemin):
        """Exporte une table en CSV (point-virgule, UTF-8 BOM) compatible Excel."""
        if table not in ("pistes", "contacts"):
            raise ValueError("Table inconnue : %s" % table)
        rows = self.conn.execute("SELECT * FROM %s ORDER BY id" % table).fetchall()
        with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            if rows:
                writer.writerow(list(rows[0].keys()))
                for r in rows:
                    writer.writerow(tuple(r))
        return len(rows)
