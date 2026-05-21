"""Mock data — FlotaLogix fleet management."""

import random
import pandas as pd
import streamlit as st
from datetime import date, timedelta

# ─── Catalogs ─────────────────────────────────────────────────────────────────
VEHICLE_TYPES = ["Camión", "Camioneta", "Van", "Trailer", "Pickup"]

BRANDS = {
    "Camión":    ["International", "Kenworth", "Freightliner", "Volvo", "Mercedes-Benz"],
    "Camioneta": ["Ford", "Chevrolet", "RAM", "Toyota", "Nissan"],
    "Van":       ["Mercedes-Benz", "Ford", "Volkswagen", "Fiat", "Peugeot"],
    "Trailer":   ["Kenworth", "Peterbilt", "Freightliner", "Volvo", "Scania"],
    "Pickup":    ["Ford", "Chevrolet", "RAM", "Toyota", "Nissan"],
}

DRIVERS = [
    "Carlos Mendoza",   "Roberto García",    "Miguel Sánchez",    "Juan Torres",
    "Alejandro Ramírez","Héctor Flores",     "Felipe Morales",    "Ernesto López",
    "Arturo Hernández", "Daniel Vázquez",    "Luis Castillo",     "Fernando Reyes",
    "Marco Gutiérrez",  "Sergio Jiménez",    "Eduardo Martínez",  "Pablo Ramos",
    "Andrés Cruz",      "Ricardo Medina",    "Oscar Vargas",      "Iván Rojas",
    "Gerardo Peña",     "Alberto Soto",      "Víctor Mora",       "Raúl Delgado",
]

SERVICE_TYPES = [
    "Cambio de aceite",
    "Rotación de llantas",
    "Frenos",
    "Afinación",
    "Transmisión",
    "Batería",
    "Suspensión",
    "Sistema eléctrico",
    "Revisión general",
    "Cambio de llantas",
    "Filtros",
    "Radiador",
    "Embrague",
]

MECHANICS = [
    "José Pérez",
    "Antonio Lima",
    "Ricardo Olvera",
    "Marcos Salinas",
    "Iván Torres",
]

PARTS_CATALOG = [
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
]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _rand_cdmx_coord(rng: random.Random):
    """Random coordinate within Mexico City metro area."""
    lat = rng.uniform(19.22, 19.58)
    lng = rng.uniform(-99.35, -98.96)
    return round(lat, 5), round(lng, 5)


def _make_plate(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPRSTUVWXYZ"
    return (
        "".join(rng.choices(letters, k=3))
        + "-"
        + "".join(rng.choices("0123456789", k=3))
        + "-"
        + rng.choice(letters)
    )


# ─── Generators ───────────────────────────────────────────────────────────────
def _generate_vehicles(n: int = 24) -> pd.DataFrame:
    rng = random.Random(42)
    rows = []
    for i in range(n):
        vtype      = rng.choice(VEHICLE_TYPES)
        brand      = rng.choice(BRANDS[vtype])
        year       = rng.randint(2015, 2022)
        lat, lng   = _rand_cdmx_coord(rng)
        risk_score = round(rng.uniform(0, 100), 1)
        risk_level = (
            "Alto"  if risk_score >= 70 else
            "Medio" if risk_score >= 40 else
            "Bajo"
        )
        total_cost = round(rng.uniform(8_000, 80_000) * (1 + risk_score / 200), 2)
        last_maint = date.today() - timedelta(days=rng.randint(10, 300))
        next_maint = last_maint + timedelta(days=rng.choice([90, 180, 365]))
        status     = rng.choices(
            ["Activo", "En taller", "Inactivo"],
            weights=[70, 20, 10],
        )[0]

        rows.append({
            "vehicle_id":             i + 1,
            "plate":                  _make_plate(rng),
            "type":                   vtype,
            "brand":                  brand,
            "year":                   year,
            "driver":                 DRIVERS[i % len(DRIVERS)],
            "lat":                    lat,
            "lng":                    lng,
            "risk_score":             risk_score,
            "risk_level":             risk_level,
            "last_maintenance":       last_maint,
            "next_maintenance":       next_maint,
            "total_maintenance_cost": total_cost,
            "odometer":               rng.randint(50_000, 400_000),
            "status":                 status,
        })
    return pd.DataFrame(rows)


def _generate_service_history(df_vehicles: pd.DataFrame, n: int = 280) -> pd.DataFrame:
    rng        = random.Random(99)
    plates     = df_vehicles["plate"].tolist()
    vmap       = df_vehicles.set_index("plate")[["vehicle_id", "type", "brand"]].to_dict("index")
    start_date = date.today() - timedelta(days=365)
    rows       = []

    for i in range(n):
        plate  = rng.choice(plates)
        stype  = rng.choice(SERVICE_TYPES)
        sdate  = start_date + timedelta(days=rng.randint(0, 365))
        parts  = rng.sample(PARTS_CATALOG, k=rng.randint(1, 4))
        hours  = round(rng.uniform(0.5, 8.0), 1)
        cost   = round(rng.uniform(800, 18_000), 2)

        rows.append({
            "service_id":   i + 1,
            "vehicle_id":   vmap[plate]["vehicle_id"],
            "plate":        plate,
            "brand":        vmap[plate]["brand"],
            "type":         vmap[plate]["type"],
            "date":         sdate,
            "service_type": stype,
            "parts_used":   ", ".join(parts),
            "hours":        hours,
            "cost":         cost,
            "mechanic":     rng.choice(MECHANICS),
            "status":       rng.choices(
                                ["Completado", "Pendiente"],
                                weights=[85, 15],
                            )[0],
        })

    return (
        pd.DataFrame(rows)
        .sort_values("date", ascending=False)
        .reset_index(drop=True)
    )


# ─── Cached accessors ─────────────────────────────────────────────────────────
@st.cache_data
def get_fleet_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (vehicles_df, service_history_df). Cached for the session."""
    df_v = _generate_vehicles(24)
    df_s = _generate_service_history(df_v)
    return df_v, df_s


def get_service_types() -> list:
    return sorted(SERVICE_TYPES)


def get_parts_catalog() -> list:
    return sorted(PARTS_CATALOG)


def get_mechanics() -> list:
    return sorted(MECHANICS)
