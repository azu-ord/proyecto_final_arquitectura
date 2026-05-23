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

> **Nota de compatibilidad:** `tools.py` usa `try/except ImportError` para el import de `strands.tool`,
> por lo que puede importarse desde contextos sin Strands instalado (e.g. el frontend de Streamlit
> que solo necesita `_cfg()`). En ese caso `@tool` actúa como decorator transparente.

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

Llama a **Claude Haiku 4.5** (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) directamente vía `boto3` para normalizar la descripción del mecánico en una sola llamada: detecta idioma, corrige ortografía y traduce al inglés si aplica.

> **Transparencia:** el agente muestra el resultado al mecánico y pide confirmación antes de proceder con `registrar_servicio`.

#### API pública

| Función | Contexto | Descripción |
|---|---|---|
| `run_normalizacion(descripcion, tipo_servicio)` | Frontend Streamlit, tests | Función pura sin dependencia de Strands |
| `normalizar_descripcion(descripcion, tipo_servicio)` | Agente Strands | Wrapper `@tool` que llama a `run_normalizacion` |

El frontend importa `run_normalizacion` directamente para evitar la dependencia de Strands:

```python
from agent.normalizer import run_normalizacion as normalizar_descripcion
```

#### Diseño de compatibilidad de entornos

`normalizer.py` usa `try/except ImportError` para el import de `strands`:

```python
try:
    from strands import tool
except ImportError:
    def tool(fn):   # no-op decorator
        return fn
```

Esto permite importar el módulo desde el entorno del frontend (`requirements-app.txt`, sin Strands)
sin errores, mientras que en el entorno del agente (con Strands instalado) el `@tool` real se aplica.

#### `run_normalizacion(descripcion, tipo_servicio)`

```python
from agent.normalizer import run_normalizacion

resultado = run_normalizacion(
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

**Degradación elegante:** cualquier fallo en Bedrock (red, credenciales, JSON inválido) retorna
la descripción original sin lanzar excepción, garantizando que `registrar_servicio` siempre pueda proceder:

```python
# Fallback — descripción original intacta
{
    "idioma": "unknown",
    "descripcion_normalizada": "se le cayo el aceite al motor, tuberia rota",
    "corrections_summary": "normalization unavailable"
}
```

#### Selección del modelo Bedrock

Se usa el cross-region inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0`.
Requisitos para que funcione en la cuenta AWS:

- Haber completado el formulario de uso de Anthropic en la consola de Bedrock (una vez por cuenta)
- El modelo debe no estar marcado como Legacy (modelos 3.x pueden quedar en estado Legacy por inactividad)
- El IAM role debe tener permiso `bedrock:InvokeModel` sobre `arn:aws:bedrock:*:*:inference-profile/us.anthropic.*`

Para verificar qué modelos Anthropic están activos en la cuenta:

```bash
set -a && . ./.env && set +a && .venv/bin/python -c "
import boto3, json
c = boto3.client('bedrock-runtime', region_name='us-east-1')
body = json.dumps({'anthropic_version':'bedrock-2023-05-31','max_tokens':10,'messages':[{'role':'user','content':'hi'}]})
models = [
    'us.anthropic.claude-haiku-4-5-20251001-v1:0',
    'us.anthropic.claude-sonnet-4-5-20250929-v1:0',
    'us.anthropic.claude-sonnet-4-6',
]
for m in models:
    try:
        c.invoke_model(modelId=m, contentType='application/json', accept='application/json', body=body)
        print(f'OK  : {m}')
    except Exception as e:
        print(f'FAIL: {m} | {str(e)[:60]}')
"
```

---

### `prompts.py`

Contiene `MECHANIC_SYSTEM_PROMPT`, el system prompt del agente. Define el rol, lineamientos de comportamiento y el flujo obligatorio de 4 pasos para registrar un servicio:

1. Recopilar todos los datos del servicio
2. Llamar a `normalizar_descripcion`
3. Mostrar resultado al mecánico y pedir confirmación si hay cambios significativos
4. Llamar a `registrar_servicio` con la descripción normalizada

---

## Integración con `frontend/app.py`

El tab "Mecánico" del frontend **no usa el agente conversacional** — es un formulario wizard paso a paso que llama a `run_normalizacion` directamente antes de confirmar el registro.

### Flujo de normalización en el wizard

```
Paso 1-7: mecánico llena el formulario
           ↓
Paso 8 (confirmación): se llama run_normalizacion una vez
           ↓
Streamlit muestra la descripción normalizada con idioma y resumen de cambios
           ↓
Mecánico confirma → registrar_servicio con descripcion_normalizada
```

### Caché de sesión

El resultado de `run_normalizacion` se guarda en `st.session_state.mec_normalized` para evitar
llamadas repetidas a Bedrock en cada rerun de Streamlit (que ocurre en cada interacción del usuario):

```python
if st.session_state.mec_normalized is None:
    st.session_state.mec_normalized = normalizar_descripcion(descripcion, tipo_servicio)

norm = st.session_state.mec_normalized
```

Se limpia al confirmar el registro o al editar respuestas.

### Hot-reload de Streamlit

Streamlit detecta cambios en `frontend/app.py` automáticamente, pero cambios en módulos externos
como `agent/normalizer.py` pueden no disparar la recarga. Ante comportamiento inesperado,
hacer un reinicio completo:

```bash
# Ctrl+C para detener, luego:
make run
```

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
     Engine oil leak detected, broken oil line.
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
| Amazon Bedrock — Claude Sonnet 4.6 (`us.anthropic.claude-sonnet-4-6`) | Modelo principal del agente |
| Amazon Bedrock — Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`) | Normalización de texto |

La región se resuelve en este orden:
1. Variable de entorno `AWS_REGION`
2. Campo `aws.region` en `config.yaml`
3. Default `us-east-1`

En local se cargan desde `.env` vía `make run`. En ECS Fargate las credenciales vienen
del IAM task role automáticamente — no se requieren cambios de código.

### Permisos IAM requeridos para el task role (ECS)

```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
  "Resource": [
    "arn:aws:bedrock:*::foundation-model/anthropic.*",
    "arn:aws:bedrock:*:*:inference-profile/us.anthropic.*"
  ]
}
```

Estos permisos ya están definidos en `infra/ecs-fargate-app.yaml` bajo `TaskRole`.
