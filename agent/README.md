# Agent — FlotaLogix Mechanic Agent

Agente conversacional para mecánicos de FlotaLogix. Permite consultar el estado de vehículos, revisar historial de mantenimiento, sugerir refacciones y registrar nuevos servicios con normalización automática de texto.

---

## Estructura del módulo

```
agent/
├── agent.py        # Construcción del agente (build_agent)
├── tools.py        # Herramientas de consulta y escritura en BD
├── normalizer.py   # Normalización de texto vía Bedrock Haiku
├── prompts.py      # System prompt del agente
└── README.md       # Este archivo
```

---

## Módulos

### `agent.py`

Punto de entrada del agente. Exporta `build_agent()`, que crea una instancia de `strands.Agent` con el modelo Bedrock configurado y las herramientas registradas.

**Uso básico:**

```python
from agent.agent import build_agent

agent = build_agent()
response = agent("¿Cuál es el estado del vehículo con placa ABC-123?")
print(str(response))
```

**En Streamlit** (mantiene memoria de conversación entre mensajes):

```python
import streamlit as st
from agent.agent import build_agent

if "mechanic_agent" not in st.session_state:
    st.session_state.mechanic_agent = build_agent()

response = st.session_state.mechanic_agent(user_input)
st.write(str(response))
```

**Herramientas registradas (`MECHANIC_TOOLS`):**

| Orden | Herramienta | Propósito |
|---|---|---|
| 1 | `consultar_estado_vehiculo` | Estado y nivel de riesgo del vehículo |
| 2 | `buscar_historial_vehiculo` | Últimos N servicios registrados |
| 3 | `sugerir_refacciones` | Refacciones comunes por tipo de servicio |
| 4 | `normalizar_descripcion` | Corrección ortográfica y traducción al inglés |
| 5 | `registrar_servicio` | INSERT en `maintenance_records` |

---

### `tools.py`

Herramientas `@tool` de Strands que el agente puede invocar. Se conectan a RDS vía SQLAlchemy; las credenciales se obtienen de AWS Secrets Manager.

#### `consultar_estado_vehiculo(placa)`

Devuelve el estado actual y nivel de riesgo de un vehículo.

```python
from agent.tools import consultar_estado_vehiculo

resultado = consultar_estado_vehiculo("ABC-123")
# {
#   "found": True,
#   "vehicle_id": "...",
#   "plate": "ABC-123",
#   "make_and_model": "Kenworth T680",
#   "risk_level": "HIGH",
#   "risk_score": 0.87,
#   "maintenance_required": True,
#   ...
# }
```

#### `buscar_historial_vehiculo(placa, n_registros=5)`

Retorna los últimos N servicios de mantenimiento (máximo 20).

```python
from agent.tools import buscar_historial_vehiculo

historial = buscar_historial_vehiculo("ABC-123", n_registros=3)
# [
#   {"record_id": 42, "service_date": ..., "common_problem": "Frenos",
#    "mechanic_notes": "PROBLEM: Frenos\nWORK_DONE: ...", "cost": 1500.0},
#   ...
# ]
```

#### `sugerir_refacciones(tipo_servicio)`

Retorna lista de refacciones comunes para el tipo de servicio indicado.

```python
from agent.tools import sugerir_refacciones

refacciones = sugerir_refacciones("Cambio de aceite")
# ["Aceite de motor 15W-40", "Filtro de aceite", "Filtro de aire"]
```

#### `registrar_servicio(placa, tipo_servicio, descripcion, refacciones, horas, costo, mecanico)`

Inserta un nuevo registro en `maintenance_records`. El campo `mechanic_notes` se almacena con el siguiente formato etiquetado:

```
PROBLEM: Cambio de aceite
WORK_DONE: Engine oil leak detected at valve cover gasket. Replaced gasket and engine oil.
PARTS_USED: Aceite de motor 15W-40, Filtro de aceite
LABOR: 2.5 hrs | TECHNICIAN: Juan Pérez
```

```python
from agent.tools import registrar_servicio

resultado = registrar_servicio(
    placa="ABC-123",
    tipo_servicio="Cambio de aceite",
    descripcion="Engine oil leak detected at valve cover gasket. Replaced gasket and engine oil.",
    refacciones=["Aceite de motor 15W-40", "Filtro de aceite"],
    horas=2.5,
    costo=850.0,
    mecanico="Juan Pérez",
)
# {"success": True, "service_id": "42", "mensaje": "Servicio #42 registrado: ..."}
```

---

### `normalizer.py`

Llama a **Claude Haiku 3.5** (`us.anthropic.claude-3-5-haiku-20241022-v1:0`) directamente vía `boto3` para normalizar la descripción del mecánico en una sola llamada: detecta idioma, corrige ortografía y traduce al inglés si aplica.

> **Transparencia:** el agente muestra el resultado al mecánico y pide confirmación antes de proceder con `registrar_servicio`.

#### `normalizar_descripcion(descripcion, tipo_servicio)`

```python
from agent.normalizer import normalizar_descripcion

resultado = normalizar_descripcion(
    descripcion="se le cayo el aceite al motor, tuberia rota",
    tipo_servicio="Cambio de aceite",
)
# {
#   "idioma": "es",
#   "descripcion_normalizada": "Engine oil leak detected, broken oil line.",
#   "corrections_summary": "Translated from Spanish, corrected spelling ('cayo' → 'cayó')"
# }
```

**Campos retornados:**

| Campo | Tipo | Descripción |
|---|---|---|
| `idioma` | `str` | Código de idioma detectado: `"es"`, `"en"` o `"unknown"` |
| `descripcion_normalizada` | `str` | Descripción corregida y en inglés |
| `corrections_summary` | `str` | Resumen en una oración de los cambios realizados |

**Degradación elegante:** si la llamada a Bedrock falla (credenciales, red, JSON inválido), retorna la descripción original sin lanzar excepción, permitiendo que `registrar_servicio` siempre pueda proceder:

```python
# Ejemplo de fallback
{
    "idioma": "unknown",
    "descripcion_normalizada": "se le cayo el aceite al motor, tuberia rota",
    "corrections_summary": "normalization unavailable"
}
```

---

### `prompts.py`

Contiene `MECHANIC_SYSTEM_PROMPT`, el system prompt del agente. Define el rol, lineamientos de comportamiento y el flujo obligatorio de 4 pasos para registrar un servicio:

1. Recopilar todos los datos del servicio
2. Llamar a `normalizar_descripcion`
3. Mostrar resultado al mecánico y pedir confirmación si hay cambios significativos
4. Llamar a `registrar_servicio` con la descripción normalizada

---

## Flujo completo de registro de servicio

```
Mecánico:  "se le cayo el aceite al motor, tuberia rota"

Agente  →  normalizar_descripcion(
               "se le cayo el aceite al motor, tuberia rota",
               "Cambio de aceite"
           )

Bedrock →  {
               "idioma": "es",
               "descripcion_normalizada": "Engine oil leak detected, broken oil line.",
               "corrections_summary": "Translated from Spanish, corrected spelling ('cayo' → 'cayó')"
           }

Agente al mecánico:
    "Normalicé la descripción:
     📝 Engine oil leak detected, broken oil line.
     (Traducido del español, 1 corrección ortográfica)
     ¿Confirmas?"

Mecánico:  "sí"

Agente  →  registrar_servicio(
               placa="ABC-123",
               tipo_servicio="Cambio de aceite",
               descripcion="Engine oil leak detected, broken oil line.",
               refacciones=["Aceite de motor 15W-40", "Filtro de aceite"],
               horas=1.5,
               costo=850.0,
               mecanico="Juan",
           )

BD mechanic_notes:
    PROBLEM: Cambio de aceite
    WORK_DONE: Engine oil leak detected, broken oil line.
    PARTS_USED: Aceite de motor 15W-40, Filtro de aceite
    LABOR: 1.5 hrs | TECHNICIAN: Juan
```

---

## Dependencias de infraestructura

| Recurso | Uso |
|---|---|
| AWS Secrets Manager | Credenciales RDS (`itam/rds/auto-repair-shop/credentials`) |
| Amazon RDS (writer) | INSERT en `maintenance_records` |
| Amazon RDS (replica) | SELECT en `vehicles`, `maintenance_records`, `risk_scores` |
| Amazon Bedrock — Claude Sonnet 4.6 | Modelo principal del agente |
| Amazon Bedrock — Claude Haiku 3.5 (`us.anthropic.claude-3-5-haiku-20241022-v1:0`) | Normalización de texto (ligero/barato) |

La región y los endpoints se leen de `config.yaml` en la raíz del proyecto. En local se usan variables de entorno (`AWS_REGION`); en ECS se usa el IAM role del task.
