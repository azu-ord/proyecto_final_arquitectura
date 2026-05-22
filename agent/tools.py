"""
Tools available to the mechanic agent.

Each function decorated with @tool becomes a callable tool for the Strands agent.
The docstring is used by the model to understand when and how to call each tool,
so keep them clear and in the same language as the system prompt.
"""

import boto3
import json
import yaml
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, text
from strands import tool

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


@lru_cache(maxsize=1)
def get_read_engine():
    c, cfg = _creds(), _cfg()
    return create_engine(
        f"postgresql+psycopg2://{c['username']}:{c['password']}"
        f"@{cfg['rds']['host_replica']}:{c['port']}/{c['dbname']}",
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
    )


@lru_cache(maxsize=1)
def get_write_engine():
    c, cfg = _creds(), _cfg()
    return create_engine(
        f"postgresql+psycopg2://{c['username']}:{c['password']}"
        f"@{cfg['rds']['host']}:{c['port']}/{c['dbname']}",
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=2,
    )


# ─── Vehicle tools ────────────────────────────────────────────────────────────

@tool
def consultar_estado_vehiculo(placa: str) -> dict:
    """
    Consulta el estado actual y nivel de riesgo de un vehículo de la flota.

    Args:
        placa: Placa del vehículo (formato AAA-000)

    Returns:
        Diccionario con estado, nivel de riesgo, score y make/model del vehículo.
    """
    with get_read_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    v.vehicle_id,
                    v.plate,
                    v.make_and_model,
                    v.vehicle_type,
                    v.year_of_manufacture,
                    r.risk_score,
                    r.risk_level,
                    r.maintenance_required,
                    r.computed_at
                FROM   vehicles v
                LEFT   JOIN risk_scores r ON v.vehicle_id = r.vehicle_id
                WHERE  v.plate = :plate
            """),
            {"plate": placa},
        ).fetchone()

    if not row:
        return {"found": False, "placa": placa, "mensaje": f"Vehículo {placa} no encontrado."}

    return {"found": True, **dict(row._mapping)}


@tool
def buscar_historial_vehiculo(placa: str, n_registros: int = 5) -> list[dict]:
    """
    Devuelve los últimos N servicios de mantenimiento registrados para un vehículo.

    Args:
        placa:       Placa del vehículo
        n_registros: Cuántos registros retornar (default 5, máximo 20)

    Returns:
        Lista de dicts con: record_id, service_date, common_problem,
        solution_used, mechanic_notes, cost.
    """
    with get_read_engine().connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    mr.record_id,
                    mr.service_date,
                    mr.common_problem,
                    mr.solution_used,
                    mr.mechanic_notes,
                    mr.cost
                FROM   maintenance_records mr
                JOIN   vehicles v ON mr.vehicle_id = v.vehicle_id
                WHERE  v.plate = :plate
                ORDER  BY mr.service_date DESC
                LIMIT  :n
            """),
            {"plate": placa, "n": min(n_registros, 20)},
        ).fetchall()

    return [dict(r._mapping) for r in rows]


# ─── Catalog tools ────────────────────────────────────────────────────────────

@tool
def sugerir_refacciones(tipo_servicio: str) -> list[str]:
    """
    Sugiere las refacciones más comunes para un tipo de servicio de mantenimiento.

    Args:
        tipo_servicio: Nombre del servicio (ej: "Cambio de aceite", "Frenos", "Afinación")

    Returns:
        Lista de nombres de refacciones recomendadas.
    """
    catalogo: dict[str, list[str]] = {
        "Cambio de aceite":  ["Aceite de motor 15W-40", "Filtro de aceite", "Filtro de aire"],
        "Frenos":            ["Pastillas de freno delanteras", "Pastillas de freno traseras",
                              "Discos de freno", "Líquido de frenos DOT4"],
        "Afinación":         ["Bujías (juego x4)", "Filtro de aire",
                              "Filtro de combustible", "Banda serpentina"],
        "Batería":           ["Batería 27D"],
        "Suspensión":        ["Amortiguador delantero", "Amortiguador trasero"],
        "Transmisión":       ["Líquido de transmisión"],
        "Radiador":          ["Termostato", "Bomba de agua"],
        "Sistema eléctrico": ["Alternador", "Motor de arranque", "Bobina de encendido"],
        "Cambio de llantas": ["Llanta 11R22.5"],
        "Embrague":          ["Banda serpentina", "Líquido de transmisión"],
    }

    refacciones = catalogo.get(tipo_servicio)
    if not refacciones:
        tipo_lower = tipo_servicio.lower()
        for key, val in catalogo.items():
            if tipo_lower in key.lower() or key.lower() in tipo_lower:
                return val
        return ["No se encontraron sugerencias para este tipo de servicio."]

    return refacciones


# ─── Write tools ──────────────────────────────────────────────────────────────

@tool
def registrar_servicio(
    placa:         str,
    tipo_servicio: str,
    descripcion:   str,
    refacciones:   list[str],
    horas:         float,
    costo:         float,
    mecanico:      str,
) -> dict:
    """
    Registra un nuevo servicio de mantenimiento en el sistema.
    Llama esta herramienta solo cuando tengas TODOS los campos completos.

    Args:
        placa:         Placa del vehículo
        tipo_servicio: Tipo de servicio realizado
        descripcion:   Descripción del trabajo realizado o problema detectado
        refacciones:   Lista de refacciones utilizadas
        horas:         Horas de trabajo invertidas
        costo:         Costo total del servicio en MXN
        mecanico:      Nombre del mecánico responsable

    Returns:
        Confirmación del registro con ID de servicio generado.
    """
    notas = f"{descripcion} | Refacciones: {', '.join(refacciones)} | {horas:.1f} hrs | {mecanico}"

    with get_write_engine().begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO maintenance_records
                    (vehicle_id, service_date, common_problem,
                     solution_used, mechanic_notes, cost, registered_at)
                SELECT
                    v.vehicle_id,
                    NOW(),
                    :problem,
                    :solution,
                    :notes,
                    :cost,
                    NOW()
                FROM vehicles v
                WHERE v.plate = :plate
                RETURNING record_id
            """),
            {
                "plate":    placa,
                "problem":  tipo_servicio,
                "solution": ", ".join(refacciones),
                "notes":    notas,
                "cost":     costo,
            },
        )
        row = result.fetchone()

    if not row:
        return {
            "success": False,
            "mensaje": f"No se encontró el vehículo con placa {placa}.",
        }

    record_id = row[0]
    return {
        "success":    True,
        "service_id": str(record_id),
        "mensaje": (
            f"Servicio #{record_id} registrado: {tipo_servicio} "
            f"en vehículo {placa} por {mecanico}. "
            f"Costo: ${costo:,.0f} MXN · {horas:.1f} hrs."
        ),
    }
