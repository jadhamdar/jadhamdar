# -*- coding: utf-8 -*-
"""Tests unitaires de la couche données (aucune interface graphique requise)."""

import os
import tempfile
import unittest
from datetime import date, timedelta

from modele import Database, parse_date, valider_contact, valider_piste


class TestValidation(unittest.TestCase):
    def test_nom_obligatoire(self):
        with self.assertRaises(ValueError):
            valider_piste({"nom": "  "})

    def test_type_invalide(self):
        with self.assertRaises(ValueError):
            valider_piste({"nom": "X", "type": "CDD"})

    def test_date_invalide(self):
        with self.assertRaises(ValueError):
            valider_piste({"nom": "X", "prochaine_relance": "31/12/2030"})

    def test_date_valide(self):
        self.assertEqual(parse_date("2030-12-31"), date(2030, 12, 31))
        self.assertIsNone(parse_date(""))

    def test_contact_sans_piste(self):
        d = valider_contact({"nom": "Jean"})
        self.assertIsNone(d["piste_id"])


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.fermer()

    def test_crud_piste(self):
        pid = self.db.ajouter_piste({"nom": "ACME", "societe": "ACME SAS", "type": "CDI",
                                     "statut": "Nouveau", "prochaine_relance": "2030-01-01"})
        row = self.db.get_piste(pid)
        self.assertEqual(row["nom"], "ACME")
        self.assertEqual(row["type"], "CDI")
        self.db.modifier_piste(pid, {"nom": "ACME", "type": "Freelance", "statut": "En cours"})
        self.assertEqual(self.db.get_piste(pid)["statut"], "En cours")
        self.db.supprimer_piste(pid)
        self.assertIsNone(self.db.get_piste(pid))

    def test_recherche_et_filtres(self):
        self.db.ajouter_piste({"nom": "Boulangerie Dupont", "type": "CDI", "statut": "Nouveau"})
        self.db.ajouter_piste({"nom": "Studio Mars", "type": "Freelance", "statut": "Gagné"})
        self.assertEqual(len(self.db.pistes()), 2)
        self.assertEqual(len(self.db.pistes(recherche="dupont")), 1)
        self.assertEqual(len(self.db.pistes(type_filtre="Freelance")), 1)
        self.assertEqual(len(self.db.pistes(statut_filtre="Gagné")), 1)

    def test_relances_actives_triees(self):
        aujourdhui = date.today()
        p1 = self.db.ajouter_piste({"nom": "A", "prochaine_relance": (aujourdhui + timedelta(days=5)).isoformat()})
        p2 = self.db.ajouter_piste({"nom": "B", "prochaine_relance": (aujourdhui - timedelta(days=2)).isoformat()})
        self.db.ajouter_piste({"nom": "C", "prochaine_relance": (aujourdhui - timedelta(days=1)).isoformat(),
                               "statut": "Gagné"})
        self.db.ajouter_piste({"nom": "D"})
        rel = self.db.relances()
        self.assertEqual([r["nom"] for r in rel], ["B", "A"])
        self.assertNotIn(p1, [r["id"] for r in rel if r["nom"] == "C"])

    def test_relance_effectuee(self):
        pid = self.db.ajouter_piste({"nom": "X", "prochaine_relance": "2000-01-01"})
        self.db.relance_effectuee(pid, jours=7)
        row = self.db.get_piste(pid)
        self.assertEqual(row["prochaine_relance"], (date.today() + timedelta(days=7)).isoformat())
        self.assertEqual(row["statut"], "Relancé")

    def test_definir_relance(self):
        pid = self.db.ajouter_piste({"nom": "X"})
        self.db.definir_relance(pid, "2031-05-05")
        self.assertEqual(self.db.get_piste(pid)["prochaine_relance"], "2031-05-05")
        with self.assertRaises(ValueError):
            self.db.definir_relance(pid, "05/05/2031")

    def test_contacts_lies_piste(self):
        pid = self.db.ajouter_piste({"nom": "P1"})
        cid = self.db.ajouter_contact({"nom": "Jean Martin", "piste_id": pid, "email": "j@x.fr"})
        self.assertEqual(self.db.get_contact(cid)["piste_nom"], "P1")
        self.assertEqual(len(self.db.contacts(recherche="martin")), 1)
        self.db.supprimer_piste(pid)
        contact = self.db.get_contact(cid)
        self.assertIsNone(contact["piste_id"])
        self.assertEqual(contact["nom"], "Jean Martin")

    def test_stats(self):
        aujourdhui = date.today().isoformat()
        self.db.ajouter_piste({"nom": "A", "type": "CDI", "statut": "Nouveau",
                               "prochaine_relance": (date.today() - timedelta(days=1)).isoformat()})
        self.db.ajouter_piste({"nom": "B", "type": "Freelance", "statut": "En cours",
                               "prochaine_relance": aujourdhui})
        self.db.ajouter_contact({"nom": "C"})
        s = self.db.stats()
        self.assertEqual(s["pistes_total"], 2)
        self.assertEqual(s["contacts_total"], 1)
        self.assertEqual(s["relance_retard"], 1)
        self.assertEqual(s["relance_aujourdhui"], 1)
        self.assertEqual(s["par_type"]["CDI"], 1)
        self.assertEqual(s["par_statut"]["En cours"], 1)

    def test_export_csv(self):
        self.db.ajouter_piste({"nom": "ACME", "type": "CDI"})
        with tempfile.TemporaryDirectory() as tmp:
            chemin = os.path.join(tmp, "pistes.csv")
            n = self.db.export_csv("pistes", chemin)
            self.assertEqual(n, 1)
            with open(chemin, encoding="utf-8-sig") as f:
                lignes = f.read().splitlines()
            self.assertEqual(len(lignes), 2)
            self.assertIn("nom", lignes[0])
            self.assertIn("ACME", lignes[1])


class TestSources(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.fermer()

    def test_seed_par_defaut(self):
        noms = [s["nom"] for s in self.db.sources()]
        self.assertIn("CollectiveWork", noms)
        self.assertIn("mon-consultant-indépendant", noms)

    def test_ajouter_et_doublon(self):
        self.db.ajouter_source("LinkedIn")
        self.assertIn("LinkedIn", [s["nom"] for s in self.db.sources()])
        with self.assertRaises(ValueError):
            self.db.ajouter_source("LinkedIn")

    def test_nom_obligatoire(self):
        with self.assertRaises(ValueError):
            self.db.ajouter_source("   ")

    def test_renommer(self):
        sid = self.db.ajouter_source("Ancien nom")
        self.db.renommer_source(sid, "Nouveau nom")
        noms = [s["nom"] for s in self.db.sources()]
        self.assertIn("Nouveau nom", noms)
        self.assertNotIn("Ancien nom", noms)
        with self.assertRaises(ValueError):
            self.db.renommer_source(sid, "CollectiveWork")

    def test_supprimer_conserve_les_pistes(self):
        sid = self.db.ajouter_source("Source X")
        self.db.ajouter_piste({"nom": "P1", "source": "Source X"})
        nb = self.db.supprimer_source(sid)
        self.assertEqual(nb, 1)
        self.assertNotIn("Source X", [s["nom"] for s in self.db.sources()])
        self.assertEqual(self.db.pistes(recherche="P1")[0]["source"], "Source X")

    def test_compteur_utilisation(self):
        self.db.ajouter_piste({"nom": "P1", "source": "CollectiveWork"})
        self.db.ajouter_piste({"nom": "P2", "source": "CollectiveWork"})
        row = [s for s in self.db.sources() if s["nom"] == "CollectiveWork"][0]
        self.assertEqual(row["nb_pistes"], 2)


if __name__ == "__main__":
    unittest.main()
