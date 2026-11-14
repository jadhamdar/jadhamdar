# MiniCRM

> Ce projet se trouve dans le sous-dossier `minicrm/` de ce dépôt : `cd minicrm` avant d'exécuter les commandes ci-dessous.

CRM local et **hors ligne** pour gérer tes pistes (CDI, freelance), tes contacts et tes rappels de relance.

Aucune dépendance externe : Python 3 (bibliothèque standard uniquement : `tkinter` + `sqlite3`).

## Fonctionnalités

- **Pistes** : nom, société, type (`CDI` / `Freelance` / `Autre`), statut (`Nouveau`, `En cours`, `Relancé`, `Gagné`, `Perdu`), source, e-mail, téléphone, prochaine relance (date), notes — avec recherche et filtres par type/statut.
- **Contacts** : nom, société, fonction, e-mail, téléphone, notes, liaison optionnelle à une piste (la suppression d'une piste conserve ses contacts).
- **Relances** : liste des pistes actives à relancer, triées par date, **en retard affichées en rouge** ; boutons pour marquer « relance faite » (décale de +7 jours) ou choisir une nouvelle date.
- **Tableau de bord** : compteurs (pistes par type et par statut, contacts, relances en retard / du jour) et les 8 prochaines relances.
- **Référentiel des sources** (onglet *Sources*) : ajouter, renommer ou supprimer les sources de pistes (ex. `CollectiveWork`, `mon-consultant-indépendant`) ; le champ *Source* de l'onglet *Pistes* est une **liste déroulante** alimentée par ce référentiel. Supprimer une source ne touche pas aux pistes existantes.
- **Export CSV** (point-virgule, compatible Excel) des pistes et des contacts via le menu *Fichier*.
- **Données locales** : tout est stocké dans `minicrm.db`, créé à côté de l'exécutable — l'application est portable (copie le `.exe` + la base sur une clé USB).

## Lancer depuis les sources

```bash
cd minicrm
python crm.py
```

(Python 3 installé, rien d'autre à installer.)

## Obtenir le `.exe` (Windows)

### Option 1 — téléchargement automatique (GitHub Releases)

Le workflow `.github/workflows/release-exe.yml` compile `MiniCRM.exe` sur une machine Windows à chaque tag `v*` (ou via l'onglet *Actions* → *Run workflow*) :

```bash
git tag v1.0.0
git push origin v1.0.0
```

Puis télécharge `MiniCRM.exe` dans l'onglet **Releases** du dépôt.

### Option 2 — compilation locale sur ta machine Windows

```bat
cd minicrm
build_exe.bat
```

ou manuellement :

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name MiniCRM crm.py
```

L'exécutable se trouve dans `dist\MiniCRM.exe`. Double-clic dessus pour lancer le CRM — aucune installation requise.

## Structure du projet

| Fichier | Rôle |
|---|---|
| `crm.py` | Interface graphique (Tkinter) |
| `modele.py` | Couche données SQLite + validation (testable sans interface) |
| `test_modele.py` | Tests unitaires (`python -m unittest test_modele`) |
| `build_exe.bat` | Compilation du `.exe` sous Windows |
| `requirements.txt` | Dépendance de build uniquement (PyInstaller) |
| `.github/workflows/release-exe.yml` | Compilation automatique du `.exe` et publication en release |

## Tests

```bash
cd minicrm
python -m unittest test_modele -v
```
