"""Data layer — FlotaLogix (RDS PostgreSQL)."""

import hashlib
import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import get_read_engine

# ─── Catálogos estáticos (no están en RDS) ────────────────────────────────────
MECHANICS = sorted([
    "José Pérez",
    "Antonio Lima",
    "Ricardo Olvera",
    "Marcos Salinas",
    "Iván Torres",
])

PARTS_CATALOG = sorted([
    "Aceite de motor 15W-40",
    "Filtro de aceite",
    "Filtro de aire",
    "Filtro de combustible",
    "Pastillas de freno delanteras",
    "Pastillas de freno traseras",
    "Discos de freno",
    "Batería 27D",
    "Llanta 11R22.5",
    "Bujías (juego x4)",
    "Banda serpentina",
    "Amortiguador delantero",
    "Amortiguador trasero",
    "Líquido de frenos DOT4",
    "Líquido de transmisión",
    "Termostato",
    "Bomba de agua",
    "Alternador",
    "Motor de arranque",
    "Bobina de encendido",
])


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _vehicle_coords(vehicle_id: int) -> tuple[float, float]:
    """Coordenadas CDMX determinísticas desde vehicle_id.

    Placeholder hasta que se agregue lat/lng a la tabla vehicles en RDS.
    """
    h = int(hashlib.md5(str(vehicle_id).encode()).hexdigest(), 16)
    lat = 19.22 + (h % 100_000) / 100_000 * (19.58 - 19.22)
    lng = -99.35 + ((h >> 20) % 100_000) / 100_000 * (-98.96 - (-99.35))
    return round(lat, 5), round(lng, 5)


# ─── Queries ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_fleet_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (vehicles_df, service_history_df) desde RDS. Cache de 5 minutos."""
    engine = get_read_engine()

    with engine.connect() as conn:
        df_v = pd.read_sql(
            text("""
                SELECT
                    v.vehicle_id,
                    v.plate,
                    v.make_and_model,
                    v.year_of_manufacture          AS year,
                    v.vehicle_type                 AS type,
                    r.risk_score,
                    r.risk_level,
                    r.maintenance_required,
                    COALESCE(m.total_cost, 0)      AS total_maintenance_cost
                FROM vehicles v
                LEFT JOIN risk_scores r
                    ON v.vehicle_id = r.vehicle_id
                LEFT JOIN (
                    SELECT vehicle_id, SUM(cost) AS total_cost
                    FROM   maintenance_records
                    GROUP  BY vehicle_id
                ) m ON v.vehicle_id = m.vehicle_id
            """),
            conn,
        )

        df_s = pd.read_sql(
            text("""
                SELECT
                    mr.record_id                   AS service_id,
                    mr.vehicle_id,
                    v.plate,
                    v.make_and_model               AS brand,
                    v.vehicle_type                 AS type,
                    mr.service_date::date          AS date,
                    mr.common_problem              AS service_type,
                    mr.solution_used               AS parts_used,
                    mr.cost,
                    mr.mechanic_notes              AS mechanic
                FROM  maintenance_records mr
                JOIN  vehicles v ON mr.vehicle_id = v.vehicle_id
                ORDER BY mr.service_date DESC
            """),
            conn,
        )

    # Extraer marca del campo make_and_model (ej. "Ford F-150" → "Ford")
    df_v["brand"] = df_v["make_and_model"].str.split().str[0]

    # Coordenadas determinísticas hasta que RDS tenga columnas lat/lng
    coords = df_v["vehicle_id"].apply(_vehicle_coords)
    df_v["lat"] = [c[0] for c in coords]
    df_v["lng"] = [c[1] for c in coords]

    return df_v, df_s


@st.cache_data(ttl=300)
def get_service_types() -> list[str]:
    """Tipos de servicio desde service_catalog."""
    engine = get_read_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT common_problem FROM service_catalog ORDER BY common_problem")
        ).fetchall()
    return [r[0] for r in rows]


def get_parts_catalog() -> list[str]:
    return PARTS_CATALOG


def get_mechanics() -> list[str]:
    return MECHANICS
