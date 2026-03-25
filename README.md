# Supervision Prometheus + Grafana — API Demo

Stack de supervision opérationnelle construite pour le projet M1 DEV EPSI 25/26.  
Elle répond en temps réel aux questions : service UP ? taux d'erreur ? latence ? saturation ?

---

## Prérequis

- Docker ≥ 24 et Docker Compose ≥ 2.20
- Ports libres : `8000`, `9090`, `9093`, `9100`, `3001`, `3100`

> Le port Grafana est `3001` (et non `3000`) car ce dernier était déjà occupé sur la machine de développement.

---

## Lancer la stack

```bash
# Cloner le repo
git clone <url-du-repo>
cd <nom-du-dossier>

# Construire et démarrer tous les services
docker compose up -d --build

# Vérifier que tout est UP
docker compose ps
```

Attendre ~15 secondes que les health checks passent, puis accéder aux interfaces :

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3001 | admin / admin |
| **Prometheus** | http://localhost:9090 | — |
| **Alertmanager** | http://localhost:9093 | — |
| **API (metrics)** | http://localhost:8000/metrics | — |

---

## Arrêter la stack

```bash
# Arrêter sans supprimer les données
docker compose down

# Arrêter ET supprimer les volumes (repart de zéro)
docker compose down -v
```

---

## Simuler du trafic

```bash
# Trafic normal continu (fond) — Ctrl+C pour arrêter
./scripts/load_test.sh normal

# Scénario de pic d'erreurs (déclenche l'alerte HighErrorRate) — s'arrête tout seul
./scripts/load_test.sh errors

# Scénario de latence élevée (déclenche HighLatencyP95) — s'arrête tout seul
./scripts/load_test.sh slow

# Tout à la fois — Ctrl+C pour arrêter
./scripts/load_test.sh all
```

> **Après avoir lancé un script**, vérifier dans cet ordre :
> 1. http://localhost:9090/alerts — l'alerte apparaît d'abord en `pending`
> 2. Attendre le délai (HighErrorRate = 2 min, HighLatencyP95 = 3 min, ApiDown = 1 min)
> 3. http://localhost:9093 — l'alerte passe en `firing` et apparaît ici

---

## Recharger la config Prometheus sans redémarrer

```bash
curl -X POST http://localhost:9090/-/reload
```

---

## Architecture

```
api (FastAPI :8000) ──scrape──► prometheus (:9090) ──alerts──► alertmanager (:9093)
node_exporter (:9100) ─────────────────────────────────────────────────────────────►
                                     │
                               datasource
                                     │
                              grafana (:3001)
                                     │
                              datasource (Loki)
                                     │
api stdout ──► promtail ──► loki (:3100)
```

Voir `docs/architecture.md` pour le schéma détaillé.

---

## Métriques utilisées et pourquoi

### Métriques applicatives (FastAPI)

| Métrique | Type | Pourquoi |
|----------|------|---------|
| `http_requests_total{handler, method, status}` | Counter | Calcul du trafic (req/s) et du taux d'erreurs par endpoint |
| `http_request_duration_seconds_bucket{handler, le}` | Histogram | Calcul des percentiles de latence (p50/p95/p99) — le SLI principal |
| `api_business_errors_total{endpoint, error_type}` | Counter | Erreurs métier applicatives (404, erreurs de validation…) |
| `api_active_users` | Gauge | Indicateur de charge applicative simulé |

### Métriques système (node_exporter)

| Métrique | Pourquoi |
|----------|---------|
| `node_cpu_seconds_total{mode}` | Utilisation CPU par mode (idle → inversion pour usage) |
| `node_memory_MemAvailable_bytes` | RAM disponible — plus précis que MemFree (inclut reclaimable) |
| `node_memory_MemTotal_bytes` | RAM totale — pour le ratio disponible/total |

### Métriques d'infrastructure

| Métrique | Pourquoi |
|----------|---------|
| `up{job}` | Health de chaque target scrapée — SLI de disponibilité |

---

## SLI / SLO

| SLI | Métrique | SLO | Fenêtre |
|-----|----------|-----|---------|
| Disponibilité | `up{job="api"}` | 100% UP | immédiat |
| Taux de succès | `http_requests_total` non-5xx | ≥ 99,5% | 5 min |
| Latence p95 | `http_request_duration_seconds` | ≤ 500 ms | 5 min |

Voir `docs/sli-slo.md` pour les justifications détaillées.

---

## Dashboards Grafana

### N1 — Vue Globale (`/d/api-n1`)

Dashboard principal — **"1 écran = 1 message"** — répond aux 4 questions fondamentales :

| Panneau | Question |
|---------|---------|
| Service UP ? | Le service est-il joignable ? |
| Trafic req/s | Quel est le volume actuel ? |
| Taux erreurs 5xx | Y a-t-il des erreurs serveur ? (SLO: < 0,5%) |
| Latence p95 | Le service est-il lent ? (SLO: < 500ms) |
| CPU / RAM | L'infra est-elle saturée ? |
| Trafic par statut | Quelle tendance sur les erreurs ? |
| Latence p50/p95/p99 | Est-ce que ça empire ? |
| Top 5 endpoints | Quel endpoint consomme le plus ? |
| Alertes actives | Qu'est-ce qui fire en ce moment ? |

- Variable `$job` pour switcher de service
- Drilldown → N2 depuis les panneaux erreurs, latence et top endpoints

### N2 — Diagnostic (`/d/api-n2`)

Dashboard de diagnostic — pour répondre à **"pourquoi ?"** après une alerte N1 :

| Panneau | Question |
|---------|---------|
| Erreurs par endpoint | Quel handler est cassé ? |
| Latence p95 par endpoint | Quel handler est lent ? |
| Répartition trafic | Quel endpoint est le plus sollicité ? |
| Taux de succès global | On respecte le SLO ? |
| CPU par mode | CPU saturé par quoi ? |
| Mémoire détaillée | Fuite mémoire ? |
| Erreurs métier | Erreurs applicatives (pas HTTP) ? |
| Logs Loki | Que disent les logs au moment du pic ? |

- Variables `$job` + `$handler` (multi-select) pour filtrer
- Panel Loki intégré pour corrélation logs ↔ métriques

---

## Alertes

| Alerte | Type | Sévérité | Condition | Délai |
|--------|------|----------|-----------|-------|
| `ApiDown` | Symptôme métier | critical | `up{job="api"} == 0` | 1 min |
| `HighErrorRate` | Symptôme métier | critical | taux 5xx > 0,5% | 2 min |
| `HighLatencyP95` | Symptôme métier | warning | p95 > 500ms | 3 min |
| `HighCPU` | Saturation | warning | CPU > 80% | 5 min |
| `LowMemory` | Saturation | warning | RAM dispo < 10% | 5 min |
| `TargetDown` | Qualité collecte | warning | toute target down | 1 min |

Chaque alerte contient : labels (`severity`, `service`, `env`) + annotations (`summary`, `description`, `runbook_url`).

Voir `docs/alerting.md` pour les runbooks complets.

### Inhibition

Si `ApiDown` fire → `HighErrorRate` et `HighLatencyP95` sont inhibées (bruit maîtrisé : inutile d'alerter sur les symptômes quand la cause racine est connue).

---

## PromQL — 6 requêtes clés

```promql
# 1. UP — disponibilité
up{job="api"}

# 2. Trafic (req/s)
sum(rate(http_requests_total{job="api"}[1m]))

# 3. Taux d'erreurs 5xx
sum(rate(http_requests_total{job="api", status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="api"}[5m]))

# 4. Latence p95
histogram_quantile(0.95,
  sum by(le) (rate(http_request_duration_seconds_bucket{job="api"}[5m]))
)

# 5. Saturation CPU
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)

# 6. Top 5 endpoints par trafic
topk(5, sum by(handler) (rate(http_requests_total{job="api"}[5m])))
```

Voir `docs/promql.md` pour la documentation complète + recording rules.

---

## Bonus — Loki : corrélation logs

```logql
# Tous les logs ERROR de l'API
{job="api"} |= `ERROR`

# Logs d'erreurs avec parsing JSON
{job="api"} | json | level=`ERROR`
```

Voir `docs/loki-logql.md` pour les requêtes documentées et les cas d'usage.

---

## Structure du repo

```
.
├── docker-compose.yml          # Stack complète
├── api/
│   ├── main.py                 # FastAPI instrumentée (6 endpoints)
│   ├── requirements.txt
│   └── Dockerfile
├── prometheus/
│   ├── prometheus.yml          # Config scrape (4 targets)
│   └── rules/
│       └── alerts.yml          # 6 alertes + 3 recording rules
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/        # Prometheus + Loki auto-provisionnés
│   │   └── dashboards/         # Pointeur vers le dossier JSON
│   └── dashboards/
│       ├── n1-overview.json    # Dashboard N1 vue globale
│       └── n2-diagnostic.json  # Dashboard N2 diagnostic
├── alertmanager/
│   └── alertmanager.yml        # Routing + inhibition rules
├── loki/
│   └── loki.yml                # Config Loki 3.0
├── promtail/
│   └── promtail.yml            # Collecte logs Docker → Loki
├── scripts/
│   └── load_test.sh            # Simulation de trafic
└── docs/
    ├── architecture.md
    ├── sli-slo.md
    ├── promql.md
    ├── alerting.md
    └── loki-logql.md
```

---

## Simuler un incident (démo)

### Scénario 1 — Pic d'erreurs (viole le SLO taux de succès)

```bash
./scripts/load_test.sh errors
```

Observation :
1. http://localhost:9090/alerts → `HighErrorRate` passe de `pending` à `firing` en ~2 min
2. http://localhost:9093 → l'alerte apparaît avec le taux d'erreur mesuré
3. http://localhost:3001/d/api-n1 → le panneau "Taux erreurs 5xx" vire au rouge

Diagnostic : http://localhost:3001/d/api-n2 → "Erreurs 5xx par endpoint" → identifier `/error` → panel Logs Loki en bas de page.

### Scénario 2 — Latence élevée (viole le SLO p95)

```bash
./scripts/load_test.sh slow
```

Observation :
1. http://localhost:9090/alerts → `HighLatencyP95` passe en `firing` en ~3 min
2. http://localhost:3001/d/api-n1 → la courbe p95 dépasse 500ms

Diagnostic : http://localhost:3001/d/api-n2 → "Latence p95 par endpoint" → identifier `/slow`.

### Scénario 3 — Service down

```bash
docker compose stop api
```

Observation :
1. http://localhost:9090/alerts → `ApiDown` fire en ~1 min, `HighErrorRate` et `HighLatencyP95` sont **inhibées** automatiquement
2. http://localhost:9093 → seul `ApiDown` apparaît (pas de bruit parasite)
3. http://localhost:3001/d/api-n1 → le panneau "Service UP ?" passe en rouge

```bash
docker compose start api   # rétablissement
```
