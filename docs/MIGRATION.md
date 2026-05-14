# Migration vers PROREALTIME V2

La V2 est un projet séparé. Elle ne remplace pas le dépôt historique.

## Correspondances principales

- Le moteur de commentaires et opportunités est dans `strategies/hold_signals.py`.
- Les règles BUY, SELL, HOLD et VAD sont dans `strategies/hold_rules.py`.
- Le rapport principal est dans `reports/hold_report.py`.
- Les scripts d'analyse historiques sont référencés dans `analysis/registry.py`.
- L'interface graphique est dans `presentation/desktop/`.

## Logique conservée

La V2 conserve les notions centrales du projet :

- Entry et Exit.
- Opp et VAD Opp.
- TS, KS et Cloud en journalier et hebdomadaire.
- Long et Short/VAD.
- filtre SENS.
- exclusions de marchés pour la VAD.
- priorité de sortie avant nouvelle entrée.

## Améliorations

- choix des fichiers depuis l'interface ;
- plus de chemins personnels codés en dur ;
- exports CSV et HTML ;
- journal intégré ;
- tests unitaires ;
- aucune exécution d'ordre réel depuis cette version.

## Lancement

```powershell
pip install -e .[dev]
prorealtime-v2 gui
```
