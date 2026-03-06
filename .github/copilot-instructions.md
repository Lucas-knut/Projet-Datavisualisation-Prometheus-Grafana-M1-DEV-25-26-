# GitHub Copilot — Instructions pour ce projet

## Contexte du projet

Stack de supervision **Prometheus + Grafana + Alertmanager + Loki** pour superviser une API FastAPI.
Projet académique M1 DEV — EPSI 25/26.

## Architecture

```
api/          → FastAPI instrumentée (métriques Prometheus + logs structurés)
prometheus/   → Config scrape + alert rules + recording rules
grafana/      → Dashboards JSON provisionnés + datasources
alertmanager/ → Config routing des alertes
loki/         → Config Loki (agrégation logs)
promtail/     → Config Promtail (collecte logs → Loki)
docs/         → Documentation technique
```

## Conventions de code

### Python (API FastAPI)
- Python 3.12, FastAPI, `prometheus_fastapi_instrumentator`
- Logs en JSON structuré sur stdout (pour Promtail/Loki)
- Toujours typer les fonctions FastAPI
- Métriques custom : préfixe `api_` + suffixe `_total` (counter), `_seconds` (histogram), sans suffixe (gauge)

### PromQL
- Toujours inclure le label `job` dans les sélecteurs : `{job="api"}`
- Utiliser `rate()` sur 2x l'intervalle de scrape minimum (scrape=15s → `rate[1m]` minimum)
- Nommer les recording rules : `job:metric:aggregation` (ex: `job:http_requests:rate1m`)
- Éviter les sélecteurs sans labels (cardinalité haute)

### Grafana
- Dashboards 100% provisionnés via JSON (dossier `grafana/dashboards/`)
- Toujours définir `uid` stable dans le JSON (pas d'auto-generate)
- Variables de template : `$job`, `$instance`, `$env`
- Unités : latence en `s` ou `ms`, CPU en `%`, RAM en `bytes`
- Titres de panneaux : phrase courte, orientée question ("Taux d'erreurs HTTP", "Latence p95")

### Alertmanager
- Toujours définir `labels.severity` : `critical` | `warning` | `info`
- Toujours définir `labels.service` et `labels.env`
- `annotations.summary` : phrase courte (< 80 chars)
- `annotations.description` : contexte + valeur mesurée
- `annotations.runbook_url` : lien vers le doc dans `docs/`

### Docker Compose
- Versions d'images explicites (pas de `latest` en prod, toléré ici pour la démo)
- Volumes nommés pour la persistance Prometheus et Grafana
- Réseau dédié `monitoring` pour l'isolation
- Health checks sur les services critiques

## SLI / SLO définis

| SLI | Métrique | SLO |
|-----|----------|-----|
| Disponibilité | `up{job="api"}` | 100% (alerte si down) |
| Taux de succès | `http_requests_total` non-5xx | ≥ 99,5% sur 5min |
| Latence p95 | `http_request_duration_seconds` histogram | ≤ 500ms |

## Requêtes PromQL de référence

```promql
# UP
up{job="api"}

# Trafic (req/s)
sum(rate(http_requests_total{job="api"}[1m]))

# Taux d'erreurs 5xx
sum(rate(http_requests_total{job="api",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="api"}[5m]))

# Latence p95
histogram_quantile(0.95, sum by(le) (rate(http_request_duration_seconds_bucket{job="api"}[5m])))

# CPU node
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)

# Top endpoints par trafic
topk(5, sum by(handler) (rate(http_requests_total{job="api"}[5m])))
```

## Commandes utiles

```bash
# Lancer la stack
docker compose up -d

# Arrêter la stack
docker compose down

# Voir les logs de l'API
docker compose logs -f api

# Recharger la config Prometheus (sans restart)
curl -X POST http://localhost:9090/-/reload

# Simuler du trafic
./scripts/load_test.sh

# Vérifier la config Prometheus
docker compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

## A ne pas faire

- Ne pas modifier les dashboards Grafana via l'UI sans exporter le JSON après
- Ne pas utiliser `latest` comme tag d'image dans un contexte de prod
- Ne pas écrire de requêtes PromQL sans labels de sélection (performance)
- Ne pas committer de secrets (mots de passe Grafana en clair dans docker-compose)
