"""RDS connection helpers — FlotaLogix.

Prioridad de configuración:
  1. Variables de entorno (ECS Fargate): DB_HOST_PRIMARY, DB_HOST_REPLICA,
     SECRET_NAME, AWS_DEFAULT_REGION
  2. config.yaml (desarrollo local)
"""

import json
import logging
import os
import socket
from functools import lru_cache
from pathlib import Path

import boto3
from sqlalchemy import create_engine

_ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _settings() -> dict:
    """Retorna host_primary, host_replica, secret_name y region."""
    # ── Desde variables de entorno (contenedor ECS) ──
    if os.environ.get("DB_HOST_PRIMARY") and os.environ.get("SECRET_NAME"):
        log.info("Loading DB settings from environment variables")
        return {
            "host_primary":  os.environ["DB_HOST_PRIMARY"],
            "host_replica":  os.environ.get("DB_HOST_REPLICA", ""),
            "secret_name":   os.environ.get("SECRET_NAME", ""),
            "region":        os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        }

    # ── Desde config.yaml (local) ──
    log.info("Loading DB settings from config.yaml")
    import yaml
    with open(_ROOT / "config.yaml") as f:
        cfg = yaml.safe_load(f)
    return {
        "host_primary": cfg["rds"]["host"],
        "host_replica": cfg["rds"].get("host_replica", ""),
        "secret_name":  cfg["aws"]["secret_name"],
        "region":       cfg["aws"]["region"],
    }


@lru_cache(maxsize=1)
def _creds() -> dict:
    s = _settings()
    log.info("Fetching DB credentials from Secrets Manager: %s", s["secret_name"])
    client = boto3.client("secretsmanager", region_name=s["region"])
    secret = client.get_secret_value(SecretId=s["secret_name"])
    return json.loads(secret["SecretString"])


def _make_engine(host: str):
    log.info("Creating SQLAlchemy engine for host=%s", host)
    c = _creds()
    return create_engine(
        f"postgresql+psycopg2://{c['username']}:{c['password']}"
        f"@{host}:{c['port']}/{c['dbname']}",
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
    )


@lru_cache(maxsize=1)
def get_read_engine():
    """Engine para SELECTs — replica si el puerto 5432 responde, si no la primaria."""
    s = _settings()
    replica = s["host_replica"]
    if replica and replica != "TBD":
        try:
            log.info("Checking read replica availability: %s", replica)
            with socket.create_connection((replica, 5432), timeout=3):
                pass
            log.info("Read replica reachable, using replica")
            return _make_engine(replica)
        except OSError:
            log.warning("Read replica unreachable, falling back to primary: %s", s["host_primary"])
            pass
    else:
        log.info("No read replica configured, using primary")
    return _make_engine(s["host_primary"])


@lru_cache(maxsize=1)
def get_write_engine():
    """Engine para INSERTs/UPDATEs — siempre la primaria."""
    log.info("Using primary engine for writes")
    return _make_engine(_settings()["host_primary"])
