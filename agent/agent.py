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

from strands import Agent, tool
from strands.models import BedrockModel

import boto3
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

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

    # En local usa variables de entorno; en ECS usa el IAM role del task
    session = boto3.Session(region_name=os.getenv("AWS_REGION", "us-east-1"))
    
    return Agent(
        system_prompt=MECHANIC_SYSTEM_PROMPT,
        tools=MECHANIC_TOOLS,
        model=BedrockModel(
              model_id="us.anthropic.claude-sonnet-4-6",
              boto_session=session,
          ),
    )
