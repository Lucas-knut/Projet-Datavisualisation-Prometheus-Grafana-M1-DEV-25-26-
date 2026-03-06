import time
import random
import logging
import sys
from fastapi import FastAPI, Response, Request
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge

# ── Logging structuré (JSON-like, pour Loki) ──────────────────────────────────
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
)
logger = logging.getLogger("api")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Demo API", description="API de démo pour supervision Prometheus/Grafana")

# ── Métriques custom ──────────────────────────────────────────────────────────
business_errors = Counter(
    "api_business_errors_total",
    "Erreurs métier applicatives",
    ["endpoint", "error_type"],
)

active_users = Gauge(
    "api_active_users",
    "Nombre d'utilisateurs actifs simulés",
)

# ── Instrumentation automatique (histograms latence + req/s par endpoint/status)
Instrumentator().instrument(app).expose(app)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check — toujours 200."""
    logger.info("health check OK")
    return {"status": "ok"}


@app.get("/")
def root():
    """Endpoint principal — simule un usage normal."""
    active_users.set(random.randint(10, 100))
    logger.info("root endpoint called")
    return {"message": "Hello from Demo API"}


@app.get("/items")
def list_items():
    """Liste d'articles — latence normale (10-80ms simulée)."""
    time.sleep(random.uniform(0.01, 0.08))
    logger.info("items listed")
    return {"items": [f"item_{i}" for i in range(random.randint(5, 20))]}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    """Détail d'un article — peut retourner 404."""
    time.sleep(random.uniform(0.01, 0.05))
    if item_id > 100:
        business_errors.labels(endpoint="/items/{item_id}", error_type="not_found").inc()
        logger.warning(f"item {item_id} not found")
        return Response(status_code=404, content=f"Item {item_id} not found")
    logger.info(f"item {item_id} fetched")
    return {"id": item_id, "name": f"Item {item_id}"}


@app.get("/slow")
def slow_endpoint():
    """Endpoint lent — latence 300ms-1200ms pour tester les alertes p95."""
    delay = random.uniform(0.3, 1.2)
    time.sleep(delay)
    logger.info(f"slow endpoint responded in {delay:.2f}s")
    return {"message": "slow response", "delay_ms": round(delay * 1000)}


@app.get("/error")
def error_endpoint():
    """Endpoint qui génère des erreurs 500 ~30% du temps."""
    if random.random() < 0.3:
        business_errors.labels(endpoint="/error", error_type="server_error").inc()
        logger.error("simulated server error triggered")
        return Response(status_code=500, content="Simulated internal error")
    logger.info("error endpoint OK this time")
    return {"message": "no error this time"}


@app.get("/cpu-intensive")
def cpu_intensive():
    """Simule un endpoint CPU-bound."""
    # Calcul inutile pour stresser légèrement le CPU
    result = sum(i * i for i in range(100_000))
    logger.info("cpu-intensive endpoint called")
    return {"result": result}
