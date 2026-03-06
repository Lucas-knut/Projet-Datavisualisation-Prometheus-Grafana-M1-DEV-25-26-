# SLI / SLO — Définitions et justifications

## Contexte

On supervise une API HTTP de démonstration dans un environnement conteneurisé.
L'objectif est de détecter rapidement toute dégradation de service et d'en identifier la cause.

---

## SLI définis (Service Level Indicators)

Les SLI sont des **métriques objectives** qui mesurent la qualité du service du point de vue de l'utilisateur.

### SLI 1 — Disponibilité

| Champ | Valeur |
|-------|--------|
| **Définition** | Le service est-il joignable et scrappable par Prometheus ? |
| **Métrique** | `up{job="api"}` |
| **Valeur bonne** | `1` (service UP) |
| **Valeur mauvaise** | `0` (service DOWN) |
| **Justification** | Un service DOWN = 0% de requêtes servies. C'est l'indicateur de base le plus critique. |

```promql
up{job="api"}
```

### SLI 2 — Taux de succès (Error Rate)

| Champ | Valeur |
|-------|--------|
| **Définition** | Proportion de requêtes HTTP ne retournant pas une erreur 5xx |
| **Métrique** | `http_requests_total{job="api"}` avec filtrage par status |
| **Calcul** | `(total_req - req_5xx) / total_req * 100` |
| **Justification** | Les erreurs 5xx sont des erreurs côté serveur — l'utilisateur ne peut rien y faire. C'est la mesure directe de la fiabilité applicative. |

```promql
(
  sum(rate(http_requests_total{job="api"}[5m]))
  - sum(rate(http_requests_total{job="api", status=~"5.."}[5m]))
)
/ sum(rate(http_requests_total{job="api"}[5m])) * 100
```

### SLI 3 — Latence p95

| Champ | Valeur |
|-------|--------|
| **Définition** | 95e percentile de la durée de réponse des requêtes HTTP |
| **Métrique** | `http_request_duration_seconds_bucket{job="api"}` (histogram) |
| **Calcul** | `histogram_quantile(0.95, ...)` |
| **Justification** | Le p95 capture les lenteurs ressenties par 5% des utilisateurs — plus représentatif que la moyenne, moins sensible aux outliers extrêmes que le p99. |

```promql
histogram_quantile(
  0.95,
  sum by(le) (rate(http_request_duration_seconds_bucket{job="api"}[5m]))
)
```

---

## SLO définis (Service Level Objectives)

Les SLO sont des **objectifs cibles** sur les SLI, avec une fenêtre temporelle.

> Note : En production réelle, la fenêtre standard est 30 jours rolling.
> Ici on utilise **5 minutes** pour permettre de simuler facilement des violations pendant la démo.

### SLO 1 — Disponibilité : 100%

| Champ | Valeur |
|-------|--------|
| **Objectif** | Service UP 100% du temps |
| **SLI associé** | Disponibilité (`up{job="api"}`) |
| **Seuil d'alerte** | Dès que `up == 0` pendant > 1 minute |
| **Justification** | Une API de production ne doit jamais être DOWN. Toute indisponibilité est un incident critique. |

### SLO 2 — Taux de succès ≥ 99,5%

| Champ | Valeur |
|-------|--------|
| **Objectif** | ≥ 99,5% de requêtes non-5xx sur 5 minutes |
| **SLI associé** | Taux de succès |
| **Seuil d'alerte** | Taux d'erreur > 0,5% pendant > 2 minutes |
| **Error budget** | 0,5% = ~3 req/min sur une API à 600 req/min |
| **Justification** | Standard pour une API interne. Permet quelques erreurs transitoires sans déclencher d'alarme intempestive, mais détecte une dégradation réelle. |

### SLO 3 — Latence p95 ≤ 500ms

| Champ | Valeur |
|-------|--------|
| **Objectif** | p95 < 500ms sur 5 minutes |
| **SLI associé** | Latence p95 |
| **Seuil d'alerte** | p95 > 500ms pendant > 3 minutes |
| **Justification** | Au-delà de 500ms, la perception utilisateur se dégrade notablement (études UX Google : +53% d'abandon si > 3s, mais la dégradation commence à 200ms). 500ms est un compromis raisonnable pour une API avec potentiellement des appels DB. |

---

## Résumé des seuils

| SLO | Métrique | Seuil | Sévérité alerte | Durée avant alerte |
|-----|----------|-------|-----------------|-------------------|
| Disponibilité | `up{job="api"}` | `== 0` | `critical` | 1 minute |
| Taux de succès | error rate | `> 0.5%` | `critical` | 2 minutes |
| Latence p95 | p95 latence | `> 500ms` | `warning` | 3 minutes |
| Saturation CPU | cpu usage | `> 80%` | `warning` | 5 minutes |
| Saturation RAM | ram available | `< 10%` | `warning` | 5 minutes |
