# Mise en place d'une supervision exploitable en production

> Sujet de projet — M1 DEV 25/26

---

## Contexte

Tu rejoins une équipe "Ops/DevOps" qui doit superviser une API web (service HTTP) et son environnement (machine/containers). On te demande une solution de supervision **Prometheus + Grafana**, avec alerting, et (optionnel) corrélation logs via Loki.

---

## Objectif du projet

Construire une stack de supervision opérationnelle qui permet de répondre rapidement aux questions :

- Le service est-il **UP** ?
- Quel est le **taux d'erreur** ?
- Quelle est la **latence (p95)** ?
- Y a-t-il de la **saturation** (CPU/RAM/IO) ?
- Qu'est-ce qui explique un **pic** (métriques ↔ logs) ?

> N'hésitez pas à mettre en évidence d'autres indicateurs.

---

## Périmètre et contraintes

| Critère | Valeur |
|---|---|
| Travail en groupe | 3 personnes max |
| Temps total | 8h maximum |
| Livrable | Solution reproductible (repo Git + instructions), pas uniquement une démo "sur une machine" |

---

## Requirements

### 1. Déploiement de la stack

Déployer (idéalement via **Docker Compose**) :

- Prometheus
- Grafana
- Alertmanager
- Au moins 1 exporter système (`node_exporter`)
- 1 cible applicative exposant des métriques HTTP (au choix : petite API instrumentée, ou une app de démo Prometheus)

---

### 2. Modèle de supervision (SLI/SLO)

- Définir **2 SLI minimum** (ex : disponibilité, p95 latence, % erreurs)
- Définir **1 SLO** (ex : "99,5% de succès sur 30 jours" ou équivalent sur une fenêtre plus courte si besoin)
- Justifier rapidement vos seuils

---

### 3. PromQL : requêtes "propres"

Fournir **au moins 6 requêtes PromQL** (documentées) couvrant :

| # | Sujet |
|---|---|
| 1 | UP |
| 2 | Trafic (req/s) |
| 3 | Erreurs (4xx/5xx ou erreurs applicatives) |
| 4 | Latence (p95 si histogram dispo) |
| 5 | Saturation (CPU/RAM/FS ou autre) |
| 6 | topk (top endpoints, top instances, etc.) |

> Appliquer la méthode **"table → validation labels/unités → graphe"** et éviter les requêtes trop coûteuses (cardinalité, fenêtres, recording rules).

---

### 4. Dashboard Grafana "1 écran = 1 message"

**Dashboard principal (vue N1) :**

- Lisible, titres explicites, unités cohérentes, **6–10 panneaux max**
- Au moins **1 variable** (service/instance/env)
- Au moins **1 drilldown** (lien vers un dashboard N2 ou vers Explore)

**Dashboard secondaire (N2 "diagnostic") :** recommandé.

---

### 5. Alerting actionnable

Créer **au moins 3 alert rules** :

| # | Type | Exemple |
|---|---|---|
| 1 | Symptôme "métier" | Taux d'erreur, disponibilité, latence |
| 2 | Saturation | Mémoire dispo faible durable, CPU high avec justification |
| 3 | Qualité de collecte | Target down / scrape en échec |

Chaque alerte doit contenir :

- **labels** : `service`, `severity`, `env`…
- **annotations** : message clair + "quoi faire" + lien dashboard/runbook

---

## Optionnel (bonus)

- Ajouter **Loki** + 2 requêtes LogQL pour corréler un pic d'erreurs/latence avec les logs
- Superviser un équipement réseau simulé / **SNMP exporter** si vous avez un support

---

## Livrables attendus

### 1. Repo Git contenant :

- `docker-compose` (ou équivalent)
- Config Prometheus + règles (alert + recording si utile)
- Export(s) des dashboards Grafana (JSON)
- Config Alertmanager (routing minimal OK)

### 2. README (2–3 pages max) :

- Comment lancer / arrêter
- Quelles métriques sont utilisées et pourquoi
- Liste des SLI/SLO + seuils
- Liens vers dashboards + explication des alertes

### 3. Restitution — 8 minutes par groupe :

| Durée | Contenu |
|---|---|
| 3 min | Contexte / choix |
| 3 min | Démonstration |
| 2 min | Incident simulé + "comment on diagnostique" |

---

## Barème (sur 20)

| Critère | Points |
|---|---|
| Stack fonctionnelle & reproductibilité | 4 pts |
| Qualité PromQL (justesse + perf + labels/unités) | 5 pts |
| Dashboard principal (lisibilité, structuration, variables/drilldown) | 5 pts |
| Alerting (actionnable, bruit maîtrisé, contexte/runbook) | 4 pts |
| Documentation + restitution | 2 pts |
| **Bonus** (Loki corrélation, recording rules pertinentes…) | **+2 pts** |

---

## Proposition de découpage (8h)

| Durée | Étape |
|---|---|
| 1h | Cadrage (SLI/SLO, architecture, choix de la cible applicative) |
| 2h | Déploiement stack + scrape OK (targets UP) |
| 2h | PromQL + recording rules si besoin |
| 2h | Dashboards (N1 + N2) |
| 1h | Alertes + README + répétition démo |
