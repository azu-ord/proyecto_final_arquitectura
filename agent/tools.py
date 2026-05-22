"""
Tools available to the mechanic agent.

Each function decorated with @tool becomes a callable tool for the Strands agent.
The docstring is used by the model to understand when and how to call each tool,
so keep them clear and in the same language as the system prompt.

TODO: Replace the mock implementations with real DB queries (SQLAlchemy / RDS)
      once the data layer is ready. The function signatures and return shapes
      should stay the same so agent.py doesn't need to change.
"""

from strands import tool


# ─── Vehicle tools ────────────────────────────────────────────────────────────

@tool
def consultar_estado_vehiculo(placa: str) -> dict:
    """
    Consulta el estado actual y nivel de riesgo de un vehículo de la flota.

    Args:
        placa: Placa del vehículo (formato AAA-000-A)

    Returns:
        Diccionario con estado, nivel de riesgo, score, conductor y
        fecha del último y próximo mantenimiento.
    """
    # TODO: reemplazar con query real
    # with get_read_engine().connect() as conn:
    #     row = conn.execute(
    #         text("SELECT * FROM vehicles WHERE plate = :plate"), {"plate": placa}
    #     ).fetchone()
    #     if not row:
    #         return {"found": False, "placa": placa}
    #     return dict(row._mapping)

    return {
        "found":             False,
        "placa":             placa,
        "mensaje":           f"Vehículo {placa} no encontrado. (implementación pendiente)",
    }


@tool
def buscar_historial_vehiculo(placa: str, n_registros: int = 5) -> list[dict]:
    """
    Devuelve los últimos N servicios de mantenimiento registrados para un vehículo.

    Args:
        placa:       Placa del vehículo
        n_registros: Cuántos registros retornar (default 5, máximo 20)

    Returns:
        Lista de dicts con: fecha, tipo_servicio, costo, mecanico, estado
    """
    # TODO: reemplazar con query real
    # with get_read_engine().connect() as conn:
    #     rows = conn.execute(
    #         text("""
    #             SELECT date, service_type, cost, mechanic, status
    #             FROM   service_history
    #             WHERE  plate = :plate
    #             ORDER  BY date DESC
    #             LIMIT  :n
    #         """),
    #         {"plate": placa, "n": min(n_registros, 20)},
    #     ).fetchall()
    #     return [dict(r._mapping) for r in rows]

    return []


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
        # fuzzy fallback: buscar por coincidencia parcial
        tipo_lower = tipo_servicio.lower()
        for key, val in catalogo.items():
            if tipo_lower in key.lower() or key.lower() in tipo_lower:
                return val
        return ["No se encontraron sugerencias para este tipo de servicio."]

    return refacciones


# ─── Write tools ──────────────────────────────────────────────────────────────

@tool
def registrar_servicio(
    placa:        str,
    tipo_servicio: str,
    descripcion:  str,
    refacciones:  list[str],
    horas:        float,
    costo:        float,
    mecanico:     str,
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
    # TODO: reemplazar con INSERT real
    # with get_write_engine().begin() as conn:
    #     result = conn.execute(
    #         text("""
    #             INSERT INTO service_history
    #               (plate, service_type, description, parts_used, hours, cost, mechanic, date, status)
    #             VALUES
    #               (:plate, :stype, :desc, :parts, :hours, :cost, :mech, NOW(), 'Completado')
    #             RETURNING service_id
    #         """),
    #         { ... }
    #     )
    #     return {"success": True, "service_id": result.fetchone()[0]}

    import uuid
    service_id = str(uuid.uuid4())[:8].upper()

    return {
        "success":    True,
        "service_id": service_id,
        "mensaje":    (
            f"Servicio {service_id} registrado: {tipo_servicio} "
            f"en vehículo {placa} por {mecanico}. "
            f"Costo: ${costo:,.0f} MXN · {horas:.1f} hrs."
        ),
    }
