# Loki — Requêtes LogQL et corrélation logs/métriques

## Contexte

Loki collecte les logs de l'API FastAPI via Promtail.  
Les logs sont émis en JSON structuré sur stdout, avec les champs :
- `time` : timestamp ISO
- `level` : niveau (`INFO`, `WARNING`, `ERROR`)
- `message` : message lisible

Label Loki : `{job="api"}` (ajouté par Promtail lors de la collecte).

---

## Requête LogQL 1 — Logs d'erreurs pour corréler un pic de 5xx

**Objectif** : Identifier les erreurs serveur au moment d'un pic d'erreurs 5xx.

```logql
{job="api"} |= `ERROR`
```

| Paramètre | Valeur |
|-----------|--------|
| Sélecteur | `{job="api"}` — tous les logs de l'API |
| Filtre | `|= "ERROR"` — contient le mot ERROR |
| Usage | Panel Logs dans Grafana N2, corrélé sur le même axe temporel que les métriques |

**Variante avec parsing JSON** (pour filtrer sur le champ `level`) :

```logql
{job="api"} | json | level=`ERROR`
```

**Variante comptage d'erreurs par minute** (metric query) :

```logql
sum(rate({job="api"} |= `ERROR` [1m]))
```

> Superposer cette courbe avec `rate(http_requests_total{status=~"5.."}[1m])` dans Grafana
> permet de valider que chaque erreur HTTP 5xx correspond bien à un log ERROR applicatif.

---

## Requête LogQL 2 — Identifier les endpoints lents au moment d'un pic de latence

**Objectif** : Retrouver dans les logs les requêtes lentes qui ont causé un pic p95.

```logql
{job="api"} |= `slow`
```

| Paramètre | Valeur |
|-----------|--------|
| Sélecteur | `{job="api"}` |
| Filtre | `|= "slow"` — messages contenant "slow" |
| Usage | Corréler avec le graphe de latence p95 du dashboard N2 |

**Variante avec extraction du délai** :

```logql
{job="api"} | json | message=~`slow endpoint.*`
```

**Variante pour voir tous les WARNING et ERROR ensemble** :

```logql
{job="api"} | json | level=~`WARNING|ERROR`
```

---

## Cas d'usage : corrélation pendant un incident

### Scénario : pic d'erreurs à 14h32

1. **Alerte reçue** : `HighErrorRate` fire → taux d'erreurs 5xx > 0,5%
2. **N1** : le graphe "Trafic par statut" montre un pic de `5xx` à 14h32
3. **N2** : "Erreurs 5xx par endpoint" pointe vers `/error`
4. **N2 — panel Logs** : requête LogQL `{job="api"} |= "ERROR"` sur la plage 14h30-14h35 → les logs montrent `"simulated server error triggered"` en rafale
5. **Conclusion** : l'endpoint `/error` a subi un trafic anormal, les erreurs sont intentionnelles (endpoint de démo) ou il faut corriger le handler

### Superposition dans Grafana (Explore)

Dans Grafana → **Explore** → choisir deux datasources en split view :
- Gauche : Prometheus → `sum(rate(http_requests_total{job="api", status=~"5.."}[1m]))`
- Droite : Loki → `{job="api"} |= "ERROR"`

Les deux courbes/logs sont alignés sur le même axe temporel.

---

## Bonnes pratiques LogQL

| Règle | Pourquoi |
|-------|---------|
| Toujours commencer par un sélecteur de labels | Les labels sont indexés — performance |
| Utiliser `|=` pour un filtre simple avant `| json` | Filtre sur la chaîne brute avant parsing = plus rapide |
| Éviter `|~ ".*pattern.*"` sur de gros volumes | Regex coûteuse sur le contenu non indexé |
| Limiter la fenêtre de temps en Explore | Loki n'est pas un moteur de recherche full-text à grande échelle |
