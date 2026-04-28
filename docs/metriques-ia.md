# Métriques IA — Module de reconnaissance alimentaire

## Protocole d'évaluation

Le module de vision est évalué sur un jeu de données de test annoté de **200 photos de repas** avec vérité terrain (labels exacts des aliments présents).

## Métriques cibles

| Métrique | Objectif | Formule |
|---|---|---|
| Précision | ≥ 80 % | TP / (TP + FP) |
| Rappel | ≥ 75 % | TP / (TP + FN) |
| F1-score | ≥ 77 % | 2 × (P × R) / (P + R) |
| Latence moyenne | < 3 s | Temps moyen sur 100 appels |

## Script de mesure

```bash
# Lancer le benchmark
python -m pytest tests/test_vision_metrics.py -v --tb=short
```

## Résultats observés (à compléter avec données réelles)

| API | Précision | Rappel | F1 | Latence moy. |
|---|---|---|---|---|
| Hugging Face (vit-base-patch16-224) | À mesurer | À mesurer | À mesurer | À mesurer |
| Google Vision API | À mesurer | À mesurer | À mesurer | À mesurer |

> **Note :** Les métriques réelles doivent être mesurées avec une clé API Hugging Face valide et un jeu de données annoté. Le script de benchmark est à compléter dans `tests/test_vision_metrics.py`.

## Facteurs d'influence

- Qualité de l'éclairage et netteté de la photo
- Nombre d'aliments visibles simultanément
- Aliments peu représentés dans ImageNet (base d'entraînement de ViT)
- Aliments transformés ou préparés (plus difficiles à classifier)
