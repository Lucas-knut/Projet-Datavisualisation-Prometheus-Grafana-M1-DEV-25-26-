# Architecture de la stack

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                       réseau: monitoring                         │
│                                                                 │
│  ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐   │
│  │  FastAPI     │   │ node_exporter │   │  Alertmanager    │   │
│  │  :8000       │   │   :9100       │   │    :9093         │   │
│  │  /metrics    │   │   /metrics    │   │                  │   │
│  └──────┬───────┘   └──────┬────────┘   └────────┬─────────┘   │
│         │                  │                     ▲             │
│         └──────────────────┼─────────────────────┘             │
│                            │ scrape (15s)    fire alerts        │
│                     ┌──────▼──────┐                            │
│                     │ Prometheus  │                             │
│                     │   :9090     │                             │
│                     │ alert rules │                             │
│                     └──────┬──────┘                            │
│                            │ datasource                        │
│                     ┌──────▼──────┐                            │
│                     │   Grafana   │                            │
│                     │   :3000     │                            │
│                     │ dashboards  │                            │
│                     └─────────────┘                            │
│                                                                 │
│  ┌──────────┐    ┌───────────┐                                  │
│  │   Loki   │◄───│ Promtail  │◄── logs stdout FastAPI           │
│  │  :3100   │    │           │                                  │
│  └──────────┘    └───────────┘                                  │
│  (bonus Loki)                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Services

### FastAPI (`:8000`)
- Rôle : cible applicative exposant des métriques HTTP
- Instrumentation : `prometheus_fastapi_instrumentator` → expose `/metrics`
- Métriques exposées :
  - `http_requests_total{handler, method, status}` — counter
  - `http_request_duration_seconds{handler, method, status}` — histogram (buckets latence)
  - `api_business_errors_total{endpoint, error_type}` — counter custom
  - `api_active_users` — gauge custom
- Logs : JSON structuré sur stdout → collectés par Promtail

### Prometheus (`:9090`)
- Rôle : collecte et stockage des métriques (TSDB)
- Scrape interval : 15s
- Targets : `api:8000`, `node_exporter:9100`, `alertmanager:9093`
- Règles : `prometheus/rules/alerts.yml` + `prometheus/rules/recording.yml`

### Grafana (`:3000`)
- Rôle : visualisation des métriques et logs
- Credentials par défaut : `admin / admin` (à changer en prod)
- Datasources provisionnées : Prometheus + Loki
- Dashboards provisionnés : N1 (vue globale) + N2 (diagnostic)

### Alertmanager (`:9093`)
- Rôle : routage et déduplication des alertes Prometheus
- Config : routing minimal vers receiver `null` (webhook configurable)

### node_exporter (`:9100`)
- Rôle : métriques système (CPU, RAM, disque, réseau, filesystem)
- Pas de configuration particulière nécessaire

### Loki (`:3100`) — bonus
- Rôle : agrégation et indexation des logs
- Labels d'indexation : `job`, `container`

### Promtail — bonus
- Rôle : collecte les logs Docker stdout → pousse vers Loki
- Cible : conteneur `api` via socket Docker

## Flux de données

```
FastAPI → /metrics → Prometheus (scrape 15s)
FastAPI → stdout (JSON) → Promtail → Loki
node_exporter → /metrics → Prometheus (scrape 15s)
Prometheus → alert firing → Alertmanager
Grafana → query → Prometheus (PromQL)
Grafana → query → Loki (LogQL)
```

## Ports exposés

| Service | Port local | Usage |
|---------|-----------|-------|
| FastAPI | 8000 | API + `/metrics` |
| Prometheus | 9090 | UI + API query |
| Grafana | 3000 | Dashboards |
| Alertmanager | 9093 | UI alertes |
| node_exporter | 9100 | Métriques système |
| Loki | 3100 | API logs |
