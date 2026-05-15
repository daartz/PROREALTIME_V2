# PROREALTIME V2

Nouvelle version isolée et autonome du projet PROREALTIME. Cette refonte est centrée sur la vraie nature de l'application: le moteur `hold_report_conditions.py` + `hold_daily_report_V4.py`, c'est-à-dire la génération quotidienne des décisions **BUY / SELL / HOLD / VAD SELL / VAD BUY / VAD HOLD** à partir du fichier `Stocks list with QUARTER.csv`.

## Principes

- Ne pas écraser l'ancien projet.
- Préserver l'esprit métier: Entry/Exit, Opp/VAD Opp, TS, KS, Cloud, Day/Week/Month/Quarter, SENS, positions et stop-loss KS.
- Supprimer les chemins personnels et les effets de bord implicites.
- Piloter l'application depuis une CLI ou une interface Tkinter.
- Remplacer les anciens scripts `ANALYSE_*.py` par des analyses V2 autonomes intégrées.
- Aucun secret dans le code; configuration par environnement.
- Mode sans exécution réelle par défaut pour toute logique opérationnelle.

## Installation

```bash
cd PROREALTIME_V2
python -m venv .venv
. .venv/Scripts/activate
pip install -e .[dev]
cp .env.example .env
```

## Workflow principal

### Interface graphique

```bash
prorealtime-v2 gui
```

L'interface permet de choisir:

- le fichier `Stocks list with QUARTER.csv`,
- le dossier de sortie `Signals`,
- le dossier `Analyse`,
- les marchés à traiter,
- les dates de récupération,
- l'activation Long et/ou VAD,
- les analyses autonomes V2 à lancer.

### Rapport Hold/VAD en CLI

```bash
prorealtime-v2 hold-report \
  --stocks-file "Analyse/Stocks list with QUARTER.csv" \
  --markets "CANADA,US ETF,DJI,NASDAQ,SP500" \
  --signals-dir "Signals" \
  --analyse-dir "Analyse"
```

## Structure métier

```text
src/prorealtime_v2/
  strategies/hold_conditions.py
  reports/hold_report.py
  gui/tk_app.py
  analysis/registry.py
  analysis/runners.py
  indicators.py
  data/yahoo.py
```

## Autonomie

La V2 n'a plus besoin de remonter vers le dossier historique pour exécuter le workflow principal ou les analyses. Les runners d'analyse sont intégrés dans `analysis/runners.py`. Pour fonctionner seule, elle a uniquement besoin de ses dépendances Python et d'un fichier `Stocks list with QUARTER.csv` placé par exemple dans `data/Analyse/`.

```bash
prorealtime-v2 analysis macd-stability \
  --stocks-file "data/Analyse/Stocks list with QUARTER.csv" \
  --markets "CANADA,US ETF,DJI,NASDAQ,SP500" \
  --output-dir "reports/analysis"
```

## Entrées attendues

Le moteur principal attend un CSV `Stocks list with QUARTER.csv` séparé par `;`, avec les colonnes historiques utilisées par la V1, notamment:

- `STOCK`, `MARKET`, `SHORT NAME`, `SCORING`, `DEVISE`, `SENS`, `SECTOR`,
- `Pos`, `BUY DATE`, `BUY PRICE`, `SELL DATE`, `SELL PRICE`,
- `QUARTER`, `Q Opp`, `qTS`, `qKS`, `qCloud`,
- `MONTH`, `M Opp`, `mTS`, `mKS`, `mCloud`,
- `4001`, `4001%`, `4002`, `4002%`, `5001`, `5001%`.

## Sorties générées

- rapport global `Holding stocks report.csv`,
- fichiers par ordre: buy/sell/hold/vad sell/vad buy/vad hold,
- fichier `Stocks failed.csv`,
- mise à jour du `Stocks list with QUARTER.csv`,
- version HTML du rapport pour consultation.

## Sécurité opérationnelle

Avant toute utilisation sensible:

1. Révoquer les secrets exposés dans l'ancien projet.
2. Configurer `.env` localement.
3. Exécuter les tests.
4. Copier ton univers dans `data/Analyse/Stocks list with QUARTER.csv`.
5. Vérifier les fichiers générés et les décisions.
6. Ne reconnecter une exécution externe qu'après validation complète.
