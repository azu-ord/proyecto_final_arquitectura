"""RDS connection helpers — FlotaLogix."""

from functools import lru_cache
from pathlib import Path
import boto3
import json
import yaml
from sqlalchemy import create_engine

_ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def _cfg() -> dict:
    with open(_ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def _creds() -> dict:
    cfg = _cfg()
    client = boto3.client("secretsmanager", region_name=cfg["aws"]["region"])
    secret = client.get_secret_value(SecretId=cfg["aws"]["secret_name"])
    return json.loads(secret["SecretString"])


def _make_engine(host: str):
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
    """Engine para SELECTs — usa la replica de lectura."""
    return _make_engine(_cfg()["rds"]["host_replica"])


@lru_cache(maxsize=1)
def get_write_engine():
    """Engine para INSERTs/UPDATEs — usa la primaria."""
    return _make_engine(_cfg()["rds"]["host"])
