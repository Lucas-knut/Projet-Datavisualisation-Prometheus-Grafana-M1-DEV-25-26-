# Requêtes PromQL — Documentation

## Méthodologie

Pour chaque requête, on suit la démarche **"table → validation labels/unités → graphe"** :
1. Exécuter en mode **Table** dans Prometheus UI pour valider les labels et valeurs
2. Vérifier que les **unités sont cohérentes** (pas de mélange bytes/bits, secondes/ms)
3. Passer en mode **Graph** pour valider l'allure temporelle

---

## Requête 1 — UP (Disponibilité)

**Objectif** : Savoir si le service API est joignable par Prometheus.

```promql
up{job="api"}
```

| Paramètre | Valeur |
|-----------|--------|
| Type de résultat | Instant vector |
| Valeur | `1` = UP, `0` = DOWN |
| Unité | booléen |
| Panel Grafana | Stat / State timeline |

**Variante multi-services** :
```promql
up{job=~"api|node_exporter|alertmanager"}
```

---

## Requête 2 — Trafic (req/s)

**Objectif** : Mesurer le débit de requêtes entrant sur l'API.

```promql
sum(rate(http_requests_total{job="api"}[1m]))
```

| Paramètre | Valeur |
|-----------|--------|
| Type de résultat | Instant vector (scalaire après sum) |
| Unité | requêtes/seconde (req/s) |
| Fenêtre `rate` | `[1m]` = 4x l'intervalle de scrape (15s) — bon compromis réactivité/bruit |
| Panel Grafana | Time series |

**Variante par endpoint** :
```promql
sum by(handler) (rate(http_requests_total{job="api"}[1m]))
```

---

## Requête 3 — Taux d'erreurs (4xx + 5xx)

**Objectif** : Mesurer la proportion de requêtes en erreur (côté client + serveur).

```promql
sum(rate(http_requests_total{job="api", status=~"[45].."}[5m]))
/ sum(rate(http_requests_total{job="api"}[5m]))
```

| Paramètre | Valeur |
|-----------|--------|
| Type de résultat | Ratio (0 à 1) |
| Unité | % (multiplier par 100 dans Grafana, ou utiliser `* 100`) |
| Fenêtre | `[5m]` — plus stable qu'1m pour un ratio |
| Panel Grafana | Time series avec seuil à 0,005 (0,5%) |

**Variante 5xx uniquement (erreurs serveur)** :
```promql
sum(rate(http_requests_total{job="api", status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="api"}[5m]))
```

**Attention** : diviser par zéro si aucune requête — utiliser `> 0` en guard ou `or vector(0)`.

---

## Requête 4 — Latence p95 (histogram)

**Objectif** : Mesurer le 95e percentile de la durée de réponse.

```promql
histogram_quantile(
  0.95,
  sum by(le) (
    rate(http_request_duration_seconds_bucket{job="api"}[5m])
  )
)
```

| Paramètre | Valeur |
|-----------|--------|
| Type de résultat | Instant vector (valeur en secondes) |
| Unité | secondes (s) → convertir en ms dans Grafana |
| `by(le)` | obligatoire pour `histogram_quantile` |
| Panel Grafana | Time series, unité `s` ou `ms` |

**Variante p50 + p95 + p99 sur un seul graphe** :
```promql
histogram_quantile(0.50, sum by(le) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))
histogram_quantile(0.95, sum by(le) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))
histogram_quantile(0.99, sum by(le) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))
```

---

## Requête 5 — Saturation (CPU + RAM)

### CPU

**Objectif** : Mesurer l'utilisation CPU de la machine hôte.

```promql
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)
```

| Paramètre | Valeur |
|-----------|--------|
| Unité | % (0 à 100) |
| Logique | `idle` = temps CPU non utilisé → on l'inverse pour avoir l'utilisation |
| Panel Grafana | Gauge ou Time series, seuil à 80% |

### RAM disponible

**Objectif** : Mesurer la mémoire disponible en pourcentage.

```promql
(node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100
```

| Paramètre | Valeur |
|-----------|--------|
| Unité | % (0 à 100) |
| Logique | `MemAvailable` inclut la mémoire reclaimable (cache/buffers) — plus précis que `MemFree` |
| Panel Grafana | Gauge, seuil d'alerte à 10% disponible |

---

## Requête 6 — topk (Top endpoints par trafic)

**Objectif** : Identifier les endpoints les plus sollicités.

```promql
topk(5, sum by(handler) (rate(http_requests_total{job="api"}[5m])))
```

| Paramètre | Valeur |
|-----------|--------|
| Type de résultat | Les 5 handlers avec le plus de trafic |
| Unité | req/s |
| Panel Grafana | Bar chart ou Table |

**Variante top endpoints par taux d'erreurs** :
```promql
topk(5,
  sum by(handler) (rate(http_requests_total{job="api", status=~"5.."}[5m]))
  / sum by(handler) (rate(http_requests_total{job="api"}[5m]))
)
```

---

## Recording Rules

Les recording rules pré-calculent les requêtes coûteuses pour améliorer les performances des dashboards.

```yaml
# prometheus/rules/recording.yml

groups:
  - name: api_recording
    interval: 30s
    rules:
      - record: job:http_requests:rate1m
        expr: sum by(job, handler, status) (rate(http_requests_total[1m]))

      - record: job:http_request_duration_seconds:p95_5m
        expr: |
          histogram_quantile(0.95,
            sum by(job, le) (rate(http_request_duration_seconds_bucket[5m]))
          )

      - record: job:http_error_rate:ratio5m
        expr: |
          sum by(job) (rate(http_requests_total{status=~"5.."}[5m]))
          / sum by(job) (rate(http_requests_total[5m]))
```

> Utiliser `job:http_request_duration_seconds:p95_5m{job="api"}` dans les dashboards
> à la place du `histogram_quantile(...)` complet → calcul mutualisé, query Grafana plus rapide.
