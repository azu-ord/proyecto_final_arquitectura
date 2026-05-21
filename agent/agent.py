"""
Mechanic agent — FlotaLogix.

Usage from Streamlit (app.py):

    from agent.agent import build_agent

    # Store the agent in session state so it keeps conversation memory
    if "mechanic_agent" not in st.session_state:
        st.session_state.mechanic_agent = build_agent()

    response = st.session_state.mechanic_agent("¿Cuál es el historial de ABC-123-X?")
    st.write(str(response))
"""

from strands import Agent

from agent.prompts import MECHANIC_SYSTEM_PROMPT
from agent.tools import (
    consultar_estado_vehiculo,
    buscar_historial_vehiculo,
    sugerir_refacciones,
    registrar_servicio,
)

# Tools exposed to the agent
MECHANIC_TOOLS = [
    consultar_estado_vehiculo,
    buscar_historial_vehiculo,
    sugerir_refacciones,
    registrar_servicio,
]


def build_agent() -> Agent:
    """
    Crea y retorna una nueva instancia del agente mecánico.

    La instancia mantiene el historial de conversación internamente,
    por eso en Streamlit se guarda en st.session_state en lugar de
    crear una nueva en cada interacción.
    """
    return Agent(
        system_prompt=MECHANIC_SYSTEM_PROMPT,
        tools=MECHANIC_TOOLS,
        # model="us.amazon.nova-pro-v1:0",  # descomentar para usar Nova en Bedrock
        # model="us.anthropic.claude-3-5-haiku-20241022-v1:0",  # opción más ligera
    )
