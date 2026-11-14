#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MiniCRM — interface graphique (Tkinter).

Onglets : Tableau de bord, Pistes (CDI / freelance), Contacts, Relances.
Lancer avec :  python crm.py
Compiler en .exe :  pyinstaller --onefile --windowed --name MiniCRM crm.py
"""

import os
import subprocess
import sys
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk

from modele import (APP_NAME, CHAMPS_CONTACT, CHAMPS_PISTE, JOURS_RELANCE_DEFAUT,
                    STATUTS_PISTE, TYPES_PISTE, Database, parse_date,
                    valider_contact, valider_piste)

AUCUNE_PISTE = "— aucune —"


class OngletPistes(ttk.Frame):
    COLS = [("id", "ID", 45), ("nom", "Nom", 150), ("societe", "Société", 140),
            ("type", "Type", 90), ("statut", "Statut", 90), ("source", "Source", 110),
            ("email", "E-mail", 180), ("telephone", "Téléphone", 120),
            ("prochaine_relance", "Prochaine relance", 120), ("notes", "Notes", 220)]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.var = {c: tk.StringVar() for c in CHAMPS_PISTE}
        self.var_recherche = tk.StringVar()
        self.filtre_type = tk.StringVar(value="Tous")
        self.filtre_statut = tk.StringVar(value="Tous")
        self._construire()
        self.rafraichir()

    def _construire(self):
        form = ttk.LabelFrame(self, text="Fiche piste")
        form.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(form, text="Nom *").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["nom"], width=30).grid(row=0, column=1, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Société").grid(row=0, column=2, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["societe"], width=26).grid(row=0, column=3, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Type").grid(row=0, column=4, sticky="e", padx=4, pady=3)
        ttk.Combobox(form, textvariable=self.var["type"], values=TYPES_PISTE,
                     state="readonly", width=12).grid(row=0, column=5, sticky="w", padx=4, pady=3)

        ttk.Label(form, text="Statut").grid(row=1, column=0, sticky="e", padx=4, pady=3)
        ttk.Combobox(form, textvariable=self.var["statut"], values=STATUTS_PISTE,
                     state="readonly", width=14).grid(row=1, column=1, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Source").grid(row=1, column=2, sticky="e", padx=4, pady=3)
        self.cb_source = ttk.Combobox(form, textvariable=self.var["source"], state="readonly", width=26)
        self.cb_source.grid(row=1, column=3, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="E-mail").grid(row=1, column=4, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["email"], width=28).grid(row=1, column=5, sticky="w", padx=4, pady=3)

        ttk.Label(form, text="Téléphone").grid(row=2, column=0, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["telephone"], width=30).grid(row=2, column=1, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Prochaine relance (AAAA-MM-JJ)").grid(row=2, column=2, sticky="e", padx=4, pady=3)
        frame_date = ttk.Frame(form)
        frame_date.grid(row=2, column=3, sticky="w", padx=4, pady=3)
        ttk.Entry(frame_date, textvariable=self.var["prochaine_relance"], width=14).pack(side="left")
        ttk.Button(frame_date, text="Aujourd'hui",
                   command=lambda: self.var["prochaine_relance"].set(date.today().isoformat())
                   ).pack(side="left", padx=4)

        ttk.Label(form, text="Notes").grid(row=3, column=0, sticky="ne", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["notes"], width=110).grid(row=3, column=1, columnspan=5, sticky="w", padx=4, pady=3)

        boutons = ttk.Frame(self)
        boutons.pack(fill="x", padx=8, pady=4)
        ttk.Button(boutons, text="Ajouter", command=self.ajouter).pack(side="left", padx=2)
        ttk.Button(boutons, text="Mettre à jour", command=self.mettre_a_jour).pack(side="left", padx=2)
        ttk.Button(boutons, text="Supprimer", command=self.supprimer).pack(side="left", padx=2)
        ttk.Button(boutons, text="Effacer le formulaire", command=self.effacer).pack(side="left", padx=2)

        barre = ttk.Frame(self)
        barre.pack(fill="x", padx=8, pady=4)
        ttk.Label(barre, text="Recherche :").pack(side="left")
        entree = ttk.Entry(barre, textvariable=self.var_recherche, width=25)
        entree.pack(side="left", padx=4)
        entree.bind("<KeyRelease>", lambda _e: self.rafraichir())
        ttk.Label(barre, text="Type :").pack(side="left", padx=(12, 2))
        cb_t = ttk.Combobox(barre, textvariable=self.filtre_type, values=["Tous"] + TYPES_PISTE,
                            state="readonly", width=10)
        cb_t.pack(side="left")
        cb_t.bind("<<ComboboxSelected>>", lambda _e: self.rafraichir())
        ttk.Label(barre, text="Statut :").pack(side="left", padx=(12, 2))
        cb_s = ttk.Combobox(barre, textvariable=self.filtre_statut, values=["Tous"] + STATUTS_PISTE,
                            state="readonly", width=12)
        cb_s.pack(side="left")
        cb_s.bind("<<ComboboxSelected>>", lambda _e: self.rafraichir())

        conteneur = ttk.Frame(self)
        conteneur.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree = ttk.Treeview(conteneur, columns=[c[0] for c in self.COLS],
                                 show="headings", selectmode="browse")
        for cid, label, largeur in self.COLS:
            self.tree.heading(cid, text=label)
            self.tree.column(cid, width=largeur, anchor="w")
        vsb = ttk.Scrollbar(conteneur, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(conteneur, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        conteneur.rowconfigure(0, weight=1)
        conteneur.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _lire_formulaire(self):
        return valider_piste({c: self.var[c].get() for c in CHAMPS_PISTE})

    def _id_selection(self):
        focus = self.tree.focus()
        if not focus:
            return None
        try:
            return int(focus)
        except ValueError:
            return None

    def ajouter(self):
        try:
            d = self._lire_formulaire()
        except ValueError as exc:
            messagebox.showerror("Piste invalide", str(exc), parent=self)
            return
        self.db.ajouter_piste(d)
        self.effacer()
        self.app.rafraichir_tout()

    def mettre_a_jour(self):
        pid = self._id_selection()
        if pid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord une piste dans la liste.", parent=self)
            return
        try:
            d = self._lire_formulaire()
        except ValueError as exc:
            messagebox.showerror("Piste invalide", str(exc), parent=self)
            return
        self.db.modifier_piste(pid, d)
        self.app.rafraichir_tout()

    def supprimer(self):
        pid = self._id_selection()
        if pid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord une piste dans la liste.", parent=self)
            return
        if not messagebox.askyesno("Confirmer", "Supprimer cette piste ?\nLes contacts liés seront conservés.", parent=self):
            return
        self.db.supprimer_piste(pid)
        self.effacer()
        self.app.rafraichir_tout()

    def effacer(self):
        for c in CHAMPS_PISTE:
            self.var[c].set("")
        self.var["type"].set(TYPES_PISTE[0])
        self.var["statut"].set(STATUTS_PISTE[0])
        self.tree.selection_set(())

    def _on_select(self, _e=None):
        pid = self._id_selection()
        if pid is None:
            return
        row = self.db.get_piste(pid)
        if row is None:
            return
        for c in CHAMPS_PISTE:
            self.var[c].set(row[c] or "")
        source = row["source"] or ""
        if source:
            valeurs = list(self.cb_source.cget("values"))
            if source not in valeurs:
                self.cb_source.configure(values=valeurs + [source])

    def selectionner(self, pid):
        iid = str(pid)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            self.tree.see(iid)
            self._on_select()

    def rafraichir(self):
        self.cb_source.configure(values=[s["nom"] for s in self.db.sources()])
        self.tree.delete(*self.tree.get_children())
        for r in self.db.pistes(self.var_recherche.get(), self.filtre_type.get(), self.filtre_statut.get()):
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=tuple(r[c] for c in [c[0] for c in self.COLS]))


class OngletContacts(ttk.Frame):
    COLS = [("id", "ID", 45), ("nom", "Nom", 160), ("societe", "Société", 140),
            ("fonction", "Fonction", 130), ("email", "E-mail", 180), ("telephone", "Téléphone", 120),
            ("piste", "Piste liée", 190), ("notes", "Notes", 220)]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.var = {c: tk.StringVar() for c in CHAMPS_CONTACT}
        self.var_recherche = tk.StringVar()
        self._pistes_map = {AUCUNE_PISTE: None}
        self._construire()
        self.rafraichir()

    def _construire(self):
        form = ttk.LabelFrame(self, text="Fiche contact")
        form.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(form, text="Nom *").grid(row=0, column=0, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["nom"], width=30).grid(row=0, column=1, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Société").grid(row=0, column=2, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["societe"], width=26).grid(row=0, column=3, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Fonction").grid(row=0, column=4, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["fonction"], width=22).grid(row=0, column=5, sticky="w", padx=4, pady=3)

        ttk.Label(form, text="E-mail").grid(row=1, column=0, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["email"], width=30).grid(row=1, column=1, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Téléphone").grid(row=1, column=2, sticky="e", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["telephone"], width=26).grid(row=1, column=3, sticky="w", padx=4, pady=3)
        ttk.Label(form, text="Piste liée").grid(row=1, column=4, sticky="e", padx=4, pady=3)
        self.cb_piste = ttk.Combobox(form, textvariable=self.var["piste_id"], state="readonly", width=30)
        self.cb_piste.grid(row=1, column=5, sticky="w", padx=4, pady=3)

        ttk.Label(form, text="Notes").grid(row=2, column=0, sticky="ne", padx=4, pady=3)
        ttk.Entry(form, textvariable=self.var["notes"], width=110).grid(row=2, column=1, columnspan=5, sticky="w", padx=4, pady=3)

        boutons = ttk.Frame(self)
        boutons.pack(fill="x", padx=8, pady=4)
        ttk.Button(boutons, text="Ajouter", command=self.ajouter).pack(side="left", padx=2)
        ttk.Button(boutons, text="Mettre à jour", command=self.mettre_a_jour).pack(side="left", padx=2)
        ttk.Button(boutons, text="Supprimer", command=self.supprimer).pack(side="left", padx=2)
        ttk.Button(boutons, text="Effacer le formulaire", command=self.effacer).pack(side="left", padx=2)

        barre = ttk.Frame(self)
        barre.pack(fill="x", padx=8, pady=4)
        ttk.Label(barre, text="Recherche :").pack(side="left")
        entree = ttk.Entry(barre, textvariable=self.var_recherche, width=25)
        entree.pack(side="left", padx=4)
        entree.bind("<KeyRelease>", lambda _e: self.rafraichir())

        conteneur = ttk.Frame(self)
        conteneur.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree = ttk.Treeview(conteneur, columns=[c[0] for c in self.COLS],
                                 show="headings", selectmode="browse")
        for cid, label, largeur in self.COLS:
            self.tree.heading(cid, text=label)
            self.tree.column(cid, width=largeur, anchor="w")
        vsb = ttk.Scrollbar(conteneur, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(conteneur, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        conteneur.rowconfigure(0, weight=1)
        conteneur.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _lire_formulaire(self):
        d = {c: self.var[c].get() for c in CHAMPS_CONTACT}
        d["piste_id"] = self._pistes_map.get(d["piste_id"], None)
        return valider_contact(d)

    def _id_selection(self):
        focus = self.tree.focus()
        if not focus:
            return None
        try:
            return int(focus)
        except ValueError:
            return None

    def ajouter(self):
        try:
            d = self._lire_formulaire()
        except ValueError as exc:
            messagebox.showerror("Contact invalide", str(exc), parent=self)
            return
        self.db.ajouter_contact(d)
        self.effacer()
        self.app.rafraichir_tout()

    def mettre_a_jour(self):
        cid = self._id_selection()
        if cid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord un contact dans la liste.", parent=self)
            return
        try:
            d = self._lire_formulaire()
        except ValueError as exc:
            messagebox.showerror("Contact invalide", str(exc), parent=self)
            return
        self.db.modifier_contact(cid, d)
        self.app.rafraichir_tout()

    def supprimer(self):
        cid = self._id_selection()
        if cid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord un contact dans la liste.", parent=self)
            return
        if not messagebox.askyesno("Confirmer", "Supprimer ce contact ?", parent=self):
            return
        self.db.supprimer_contact(cid)
        self.effacer()
        self.app.rafraichir_tout()

    def effacer(self):
        for c in CHAMPS_CONTACT:
            self.var[c].set("")
        self.var["piste_id"].set(AUCUNE_PISTE)
        self.tree.selection_set(())

    def _on_select(self, _e=None):
        cid = self._id_selection()
        if cid is None:
            return
        row = self.db.get_contact(cid)
        if row is None:
            return
        for c in ["nom", "societe", "fonction", "email", "telephone", "notes"]:
            self.var[c].set(row[c] or "")
        if row["piste_id"]:
            label = "%d — %s" % (row["piste_id"], row["piste_nom"] or "")
            self._pistes_map[label] = row["piste_id"]
            self.var["piste_id"].set(label)
        else:
            self.var["piste_id"].set(AUCUNE_PISTE)

    def rafraichir(self):
        self._pistes_map = {AUCUNE_PISTE: None}
        for p in self.db.pistes():
            label = "%d — %s (%s)" % (p["id"], p["nom"], p["societe"] or "sans société")
            self._pistes_map[label] = p["id"]
        self.cb_piste.configure(values=list(self._pistes_map.keys()))
        if self.var["piste_id"].get() not in self._pistes_map:
            self.var["piste_id"].set(AUCUNE_PISTE)

        self.tree.delete(*self.tree.get_children())
        for r in self.db.contacts(self.var_recherche.get()):
            piste = ("%d — %s" % (r["piste_id"], r["piste_nom"])) if r["piste_id"] else ""
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=(r["id"], r["nom"], r["societe"], r["fonction"], r["email"],
                                     r["telephone"], piste, r["notes"]))


class OngletRelances(ttk.Frame):
    COLS = [("prochaine_relance", "Prochaine relance", 130), ("retard", "En retard", 80),
            ("nom", "Nom", 170), ("societe", "Société", 150), ("type", "Type", 90),
            ("statut", "Statut", 90), ("telephone", "Téléphone", 130), ("email", "E-mail", 200)]

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self._construire()
        self.rafraichir()

    def _construire(self):
        haut = ttk.Frame(self)
        haut.pack(fill="x", padx=8, pady=8)
        ttk.Label(haut, text="Pistes à relancer (statuts actifs), triées par date. Les lignes en rouge sont en retard.").pack(side="left")
        boutons = ttk.Frame(self)
        boutons.pack(fill="x", padx=8, pady=4)
        ttk.Button(boutons, text="Relance faite (+%d jours)" % JOURS_RELANCE_DEFAUT,
                   command=self.relance_faite).pack(side="left", padx=2)
        ttk.Button(boutons, text="Choisir une date…", command=self.nouvelle_date).pack(side="left", padx=2)
        ttk.Button(boutons, text="Ouvrir la piste", command=self.ouvrir_piste).pack(side="left", padx=2)

        conteneur = ttk.Frame(self)
        conteneur.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree = ttk.Treeview(conteneur, columns=[c[0] for c in self.COLS],
                                 show="headings", selectmode="browse")
        for cid, label, largeur in self.COLS:
            self.tree.heading(cid, text=label)
            self.tree.column(cid, width=largeur, anchor="w")
        self.tree.tag_configure("retard", foreground="#c00000", font=("TkDefaultFont", 9, "bold"))
        vsb = ttk.Scrollbar(conteneur, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(conteneur, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        conteneur.rowconfigure(0, weight=1)
        conteneur.columnconfigure(0, weight=1)

    def _id_selection(self):
        focus = self.tree.focus()
        if not focus:
            return None
        try:
            return int(focus)
        except ValueError:
            return None

    def relance_faite(self):
        pid = self._id_selection()
        if pid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord une relance dans la liste.", parent=self)
            return
        self.db.relance_effectuee(pid)
        self.app.rafraichir_tout()

    def nouvelle_date(self):
        pid = self._id_selection()
        if pid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord une relance dans la liste.", parent=self)
            return
        saisie = simpledialog.askstring("Nouvelle date de relance", "Date au format AAAA-MM-JJ :", parent=self)
        if saisie is None:
            return
        try:
            parse_date(saisie)
        except ValueError:
            messagebox.showerror("Date invalide", "Format attendu : AAAA-MM-JJ.", parent=self)
            return
        self.db.definir_relance(pid, saisie)
        self.app.rafraichir_tout()

    def ouvrir_piste(self):
        pid = self._id_selection()
        if pid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord une relance dans la liste.", parent=self)
            return
        self.app.notebook.select(self.app.tab_pistes)
        self.app.tab_pistes.selectionner(pid)

    def rafraichir(self):
        aujourdhui = date.today().isoformat()
        self.tree.delete(*self.tree.get_children())
        for r in self.db.relances():
            en_retard = r["prochaine_relance"] < aujourdhui
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=(r["prochaine_relance"], "Oui" if en_retard else "",
                                     r["nom"], r["societe"], r["type"], r["statut"],
                                     r["telephone"], r["email"]),
                             tags=("retard",) if en_retard else ())


class OngletSources(ttk.Frame):
    """Référentiel des sources de pistes : ajouter, renommer, supprimer."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.var_nom = tk.StringVar()
        self._construire()
        self.rafraichir()

    def _construire(self):
        haut = ttk.Frame(self)
        haut.pack(fill="x", padx=8, pady=8)
        ttk.Label(haut, text="Source :").pack(side="left")
        ttk.Entry(haut, textvariable=self.var_nom, width=40).pack(side="left", padx=4)
        ttk.Button(haut, text="Ajouter", command=self.ajouter).pack(side="left", padx=2)
        ttk.Button(haut, text="Renommer la sélection", command=self.renommer).pack(side="left", padx=2)
        ttk.Button(haut, text="Supprimer la sélection", command=self.supprimer).pack(side="left", padx=2)
        ttk.Button(haut, text="Effacer", command=lambda: self.var_nom.set("")).pack(side="left", padx=2)

        conteneur = ttk.Frame(self)
        conteneur.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree = ttk.Treeview(conteneur, columns=("id", "nom", "nb_pistes"),
                                 show="headings", selectmode="browse")
        for cid, label, largeur in [("id", "ID", 50), ("nom", "Source", 320),
                                    ("nb_pistes", "Pistes utilisant cette source", 240)]:
            self.tree.heading(cid, text=label)
            self.tree.column(cid, width=largeur, anchor="w")
        vsb = ttk.Scrollbar(conteneur, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        conteneur.rowconfigure(0, weight=1)
        conteneur.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _id_selection(self):
        focus = self.tree.focus()
        if not focus:
            return None
        try:
            return int(focus)
        except ValueError:
            return None

    def _on_select(self, _e=None):
        focus = self.tree.focus()
        if not focus:
            return
        valeurs = self.tree.item(focus, "values")
        self.var_nom.set(valeurs[1] if len(valeurs) > 1 else "")

    def ajouter(self):
        try:
            self.db.ajouter_source(self.var_nom.get())
        except ValueError as exc:
            messagebox.showerror("Source invalide", str(exc), parent=self)
            return
        self.var_nom.set("")
        self.app.rafraichir_tout()

    def renommer(self):
        sid = self._id_selection()
        if sid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord une source dans la liste.", parent=self)
            return
        try:
            self.db.renommer_source(sid, self.var_nom.get())
        except ValueError as exc:
            messagebox.showerror("Source invalide", str(exc), parent=self)
            return
        self.app.rafraichir_tout()

    def supprimer(self):
        sid = self._id_selection()
        if sid is None:
            messagebox.showinfo("Aucune sélection", "Sélectionne d'abord une source dans la liste.", parent=self)
            return
        valeurs = self.tree.item(self.tree.focus(), "values")
        nom, nb = valeurs[1], int(valeurs[2])
        msg = "Supprimer la source « %s » du référentiel ?" % nom
        if nb:
            msg += "\n\n%d piste(s) l'utilisent : elles conserveront la valeur « %s »." % (nb, nom)
        if not messagebox.askyesno("Confirmer", msg, parent=self):
            return
        self.db.supprimer_source(sid)
        self.var_nom.set("")
        self.app.rafraichir_tout()

    def rafraichir(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.db.sources():
            self.tree.insert("", "end", iid=str(r["id"]),
                             values=(r["id"], r["nom"], r["nb_pistes"]))


class OngletDashboard(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self._construire()
        self.rafraichir()

    def _construire(self):
        haut = ttk.Frame(self)
        haut.pack(fill="x", padx=8, pady=8)
        ttk.Button(haut, text="Rafraîchir", command=self.app.rafraichir_tout).pack(side="left")

        cartes = ttk.Frame(self)
        cartes.pack(fill="x", padx=8, pady=4)

        def carte(parent, titre):
            f = ttk.LabelFrame(parent, text=titre)
            f.pack(side="left", fill="both", expand=True, padx=4, pady=4)
            return f

        self.var_total = tk.StringVar()
        self.var_contacts = tk.StringVar()
        f1 = carte(cartes, "Vue d'ensemble")
        ttk.Label(f1, textvariable=self.var_total, font=("TkDefaultFont", 11, "bold")).pack(padx=8, pady=4)
        ttk.Label(f1, textvariable=self.var_contacts).pack(padx=8, pady=4)

        self.var_retard = tk.StringVar()
        self.var_aujourdhui = tk.StringVar()
        f2 = carte(cartes, "Relances")
        ttk.Label(f2, textvariable=self.var_retard, foreground="#c00000",
                  font=("TkDefaultFont", 11, "bold")).pack(padx=8, pady=4)
        ttk.Label(f2, textvariable=self.var_aujourdhui).pack(padx=8, pady=4)

        self.var_types = tk.StringVar()
        f3 = carte(cartes, "Pistes par type")
        ttk.Label(f3, textvariable=self.var_types, justify="left").pack(padx=8, pady=4)

        self.var_statuts = tk.StringVar()
        f4 = carte(cartes, "Pistes par statut")
        ttk.Label(f4, textvariable=self.var_statuts, justify="left").pack(padx=8, pady=4)

        bas = ttk.LabelFrame(self, text="Prochaines relances")
        bas.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree = ttk.Treeview(bas, columns=("date", "nom", "societe", "statut"),
                                 show="headings", height=8)
        for cid, label, largeur in [("date", "Date", 120), ("nom", "Nom", 200),
                                    ("societe", "Société", 200), ("statut", "Statut", 120)]:
            self.tree.heading(cid, text=label)
            self.tree.column(cid, width=largeur, anchor="w")
        vsb = ttk.Scrollbar(bas, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        vsb.pack(side="left", fill="y", pady=4, padx=(0, 4))

    def rafraichir(self):
        s = self.db.stats()
        self.var_total.set("%d piste(s) au total" % s["pistes_total"])
        self.var_contacts.set("%d contact(s)" % s["contacts_total"])
        self.var_retard.set("%d relance(s) en retard" % s["relance_retard"])
        self.var_aujourdhui.set("%d relance(s) aujourd'hui" % s["relance_aujourdhui"])
        self.var_types.set("\n".join("%s : %d" % (t, n) for t, n in s["par_type"].items()))
        self.var_statuts.set("\n".join("%s : %d" % (t, n) for t, n in s["par_statut"].items()))
        self.tree.delete(*self.tree.get_children())
        for r in self.db.relances()[:8]:
            self.tree.insert("", "end", values=(r["prochaine_relance"], r["nom"], r["societe"], r["statut"]))


class App(tk.Tk):
    def __init__(self, db_file=None):
        super().__init__()
        self.title("%s — CRM local (pistes, contacts, relances)" % APP_NAME)
        self.geometry("1180x700")
        self.db = Database(db_file)
        self.protocol("WM_DELETE_WINDOW", self._quitter)
        self._menu()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)
        self.tab_dashboard = OngletDashboard(self.notebook, self)
        self.tab_pistes = OngletPistes(self.notebook, self)
        self.tab_contacts = OngletContacts(self.notebook, self)
        self.tab_relances = OngletRelances(self.notebook, self)
        self.tab_sources = OngletSources(self.notebook, self)
        for tab, titre in ((self.tab_dashboard, "Tableau de bord"),
                           (self.tab_pistes, "Pistes"),
                           (self.tab_contacts, "Contacts"),
                           (self.tab_relances, "Relances"),
                           (self.tab_sources, "Sources")):
            self.notebook.add(tab, text=titre)
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self.rafraichir_tout())

    def rafraichir_tout(self):
        for tab in (self.tab_dashboard, self.tab_pistes, self.tab_contacts,
                    self.tab_relances, self.tab_sources):
            tab.rafraichir()

    def _menu(self):
        menu = tk.Menu(self)
        fichier = tk.Menu(menu, tearoff=0)
        fichier.add_command(label="Exporter les pistes (CSV)…", command=lambda: self._export("pistes"))
        fichier.add_command(label="Exporter les contacts (CSV)…", command=lambda: self._export("contacts"))
        fichier.add_separator()
        fichier.add_command(label="Ouvrir le dossier des données", command=self._ouvrir_dossier)
        fichier.add_separator()
        fichier.add_command(label="Quitter", command=self._quitter)
        menu.add_cascade(label="Fichier", menu=fichier)
        aide = tk.Menu(menu, tearoff=0)
        aide.add_command(label="À propos", command=self._apropos)
        menu.add_cascade(label="Aide", menu=aide)
        self.config(menu=menu)

    def _export(self, table):
        chemin = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=table + ".csv",
                                               filetypes=[("Fichier CSV", "*.csv")])
        if not chemin:
            return
        try:
            n = self.db.export_csv(table, chemin)
        except OSError as exc:
            messagebox.showerror("Export impossible", str(exc), parent=self)
            return
        messagebox.showinfo("Export terminé", "%d ligne(s) exportée(s) dans :\n%s" % (n, chemin), parent=self)

    def _ouvrir_dossier(self):
        dossier = os.path.dirname(os.path.abspath(self.db.path))
        try:
            if sys.platform.startswith("win"):
                os.startfile(dossier)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", dossier])
            else:
                subprocess.Popen(["xdg-open", dossier])
        except OSError as exc:
            messagebox.showerror("Impossible d'ouvrir le dossier", str(exc), parent=self)

    def _apropos(self):
        messagebox.showinfo("À propos de %s" % APP_NAME,
                            "%s — CRM local et hors ligne.\n\nPistes (CDI / freelance), contacts, "
                            "rappels de relance, export CSV.\n\nDonnées : %s" % (APP_NAME, self.db.path),
                            parent=self)

    def _quitter(self):
        self.db.fermer()
        self.destroy()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
