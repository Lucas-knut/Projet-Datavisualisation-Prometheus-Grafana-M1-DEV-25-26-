# Alertes — Documentation et Runbooks

## Conventions

Chaque alerte contient :
- `labels.severity` : `critical` | `warning` | `info`
- `labels.service` : nom du service concerné
- `labels.env` : environnement (`demo`, `staging`, `prod`)
- `annotations.summary` : phrase courte (< 80 chars)
- `annotations.description` : contexte + valeur mesurée
- `annotations.runbook_url` : lien vers la section runbook ci-dessous

---

## Alerte 1 — `ApiDown` (critique, symptôme métier)

### Définition

```yaml
alert: ApiDown
expr: up{job="api"} == 0
for: 1m
labels:
  severity: critical
  service: api
  env: demo
annotations:
  summary: "API demo indisponible"
  description: "Le service {{ $labels.job }} ({{ $labels.instance }}) est DOWN depuis plus d'1 minute."
  runbook_url: "http://localhost:3000/d/api-n1?orgId=1"
```

### Runbook

**Symptôme** : Prometheus ne peut plus scrapper l'API.

**Diagnostic** :
1. Vérifier que le conteneur tourne : `docker compose ps api`
2. Consulter les logs : `docker compose logs --tail=50 api`
3. Vérifier le réseau Docker : `docker compose exec prometheus wget -qO- http://api:8000/health`

**Actions** :
- Si le conteneur est arrêté : `docker compose up -d api`
- Si le conteneur est en crash loop : analyser les logs, corriger le bug, rebuilder
- Si problème réseau : `docker compose restart`

---

## Alerte 2 — `HighErrorRate` (critique, symptôme métier)

### Définition

```yaml
alert: HighErrorRate
expr: |
  sum(rate(http_requests_total{job="api", status=~"5.."}[5m]))
  / sum(rate(http_requests_total{job="api"}[5m])) > 0.005
for: 2m
labels:
  severity: critical
  service: api
  env: demo
annotations:
  summary: "Taux d'erreurs 5xx élevé sur l'API"
  description: "Taux d'erreur actuel : {{ $value | humanizePercentage }}. SLO = 99,5% de succès."
  runbook_url: "http://localhost:3000/d/api-n2?orgId=1"
```

### Runbook

**Symptôme** : Plus de 0,5% des requêtes retournent une erreur 5xx.

**Diagnostic** :
1. Aller sur le dashboard N2 → section "Erreurs par endpoint"
2. Identifier quel handler génère les 5xx : `topk(5, sum by(handler) (rate(...)))`
3. Consulter les logs Loki : `{job="api"} |= "ERROR"`
4. Corréler temporellement : quand a commencé le pic ?

**Actions** :
- Bug applicatif → corriger le code, redéployer
- Surcharge → scaler horizontalement ou limiter le trafic entrant
- Dépendance externe en erreur → circuit breaker, fallback

---

## Alerte 3 — `HighLatencyP95` (warning, symptôme métier)

### Définition

```yaml
alert: HighLatencyP95
expr: |
  histogram_quantile(0.95,
    sum by(le) (rate(http_request_duration_seconds_bucket{job="api"}[5m]))
  ) > 0.5
for: 3m
labels:
  severity: warning
  service: api
  env: demo
annotations:
  summary: "Latence p95 API au-dessus de 500ms"
  description: "p95 actuel : {{ $value | humanizeDuration }}. SLO = p95 < 500ms."
  runbook_url: "http://localhost:3000/d/api-n2?orgId=1"
```

### Runbook

**Symptôme** : 5% des requêtes prennent plus de 500ms.

**Diagnostic** :
1. Dashboard N2 → graphe latence p50/p95/p99 → identifier la tendance
2. Croiser avec le CPU : `100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100`
3. Vérifier si c'est un endpoint spécifique (ex: `/slow`, `/cpu-intensive`)
4. Consulter les logs pour des traces de timeout ou de requêtes lentes

**Actions** :
- Si CPU saturé → voir alerte `HighCPU`
- Si endpoint spécifique → optimiser la requête / ajouter du cache
- Si global → vérifier les ressources du conteneur (CPU limit trop basse ?)

---

## Alerte 4 — `HighCPU` (warning, saturation)

### Définition

```yaml
alert: HighCPU
expr: |
  100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
for: 5m
labels:
  severity: warning
  service: node
  env: demo
annotations:
  summary: "CPU élevé sur {{ $labels.instance }}"
  description: "CPU usage : {{ $value | humanize }}%. Seuil = 80%."
  runbook_url: "http://localhost:3000/d/api-n2?orgId=1"
```

### Runbook

**Symptôme** : Utilisation CPU > 80% pendant 5 minutes consécutives.

**Diagnostic** :
1. Identifier le processus consommateur : `docker stats` sur la machine hôte
2. Vérifier si le trafic est anormalement élevé (trafic req/s)
3. Vérifier si un endpoint CPU-bound est appelé excessivement (`/cpu-intensive`)

**Actions** :
- Réduire le trafic vers l'endpoint coûteux
- Augmenter les ressources CPU allouées au conteneur
- Optimiser l'algorithme si CPU-bound

---

## Alerte 5 — `TargetDown` (warning, qualité de collecte)

### Définition

```yaml
alert: TargetDown
expr: up == 0
for: 1m
labels:
  severity: warning
  service: "{{ $labels.job }}"
  env: demo
annotations:
  summary: "Target Prometheus down : {{ $labels.job }}"
  description: "La target {{ $labels.instance }} (job={{ $labels.job }}) ne répond plus au scrape."
  runbook_url: "http://localhost:3000/d/api-n1?orgId=1"
```

### Runbook

**Symptôme** : Prometheus ne peut plus scrapper une target (n'importe laquelle).

**Diagnostic** :
1. Aller sur `http://localhost:9090/targets` pour voir quelle target est DOWN
2. Vérifier l'état du conteneur : `docker compose ps <service>`
3. Tester la connectivité depuis Prometheus : `docker compose exec prometheus wget -qO- http://<service>:<port>/metrics`

**Actions** :
- Redémarrer le service concerné : `docker compose restart <service>`
- Si persistant : analyser les logs du service
