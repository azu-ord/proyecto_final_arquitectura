"""
Text normalization tool for the FlotaLogix mechanic agent.

Calls Bedrock (Claude Haiku 3.5) directly via boto3 to detect language,
correct spelling, and translate mechanic descriptions to English.

Public API
----------
normalizar_descripcion   — Strands @tool (used by the conversational agent)
run_normalizacion        — Plain function (used directly by the Streamlit frontend)
"""

import json
import logging
import re
import boto3

try:
    from strands import tool
except ImportError:
    # Strands is not available in the Streamlit frontend environment.
    # Fall back to a no-op decorator so the module loads without errors.
    def tool(fn):  # type: ignore[misc]
        return fn

from agent.tools import _cfg

log = logging.getLogger("normalizer")


def _parse_llm_json(raw: str) -> dict | None:
    """Extract and parse a JSON object from an LLM response string.

    Handles plain JSON and responses wrapped in markdown code fences.
    Returns None if parsing fails.
    """
    text = raw.strip()

    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def run_normalizacion(descripcion: str, tipo_servicio: str) -> dict:
    """Normalize a mechanic's service description via Bedrock Haiku.

    This is the plain implementation — no Strands dependency — callable from
    any context (Streamlit frontend, agent tool, tests, etc.).

    Args:
        descripcion:   Raw description written by the mechanic.
        tipo_servicio: Type of service being performed.

    Returns:
        Dictionary with keys:
          - idioma: "es", "en", or "unknown"
          - descripcion_normalizada: corrected English description
          - corrections_summary: one-sentence summary of changes made
    """
    fallback = {
        "idioma": "unknown",
        "descripcion_normalizada": descripcion,
        "corrections_summary": "normalization unavailable",
    }

    try:
        cfg = _cfg()
        region = cfg.get("aws", {}).get("region", "us-east-1")

        log.info(
            "normalizar_descripcion: Bedrock call | service=%r | input_len=%d chars",
            tipo_servicio,
            len(descripcion),
        )

        client = boto3.client("bedrock-runtime", region_name=region)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "system": (
                "You are a text normalization engine for a vehicle maintenance system. "
                "You must respond with ONLY a valid JSON object — no markdown, no explanation, "
                "no code fences. Your output must be parseable by json.loads() directly."
            ),
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Normalize the following mechanic's service description.\n\n"
                        f"Service type: {tipo_servicio}\n"
                        f"Description: {descripcion}\n\n"
                        "Return a JSON object with exactly these keys:\n"
                        '  "idioma": the detected language code ("es" or "en")\n'
                        '  "descripcion_normalizada": the description corrected for spelling, '
                        "translated to English if needed, in clear technical English\n"
                        '  "corrections_summary": brief one-sentence note on what was changed; '
                        'use "No changes needed" if input was already correct English\n\n'
                        "Respond with ONLY the JSON object."
                    ),
                }
            ],
        }

        response = client.invoke_model(
            modelId="us.anthropic.claude-3-5-haiku-20241022-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )

        raw = json.loads(response["body"].read())["content"][0]["text"]
        parsed = _parse_llm_json(raw)

        if parsed is None:
            log.warning("normalizar_descripcion: JSON parse failed, returning fallback")
            return fallback

        result = {
            "idioma": parsed.get("idioma", "unknown"),
            "descripcion_normalizada": parsed.get("descripcion_normalizada", descripcion),
            "corrections_summary": parsed.get("corrections_summary", "normalization unavailable"),
        }
        log.info(
            "normalizar_descripcion: OK | idioma=%s | summary=%r",
            result["idioma"],
            result["corrections_summary"],
        )
        return result

    except Exception as exc:
        log.warning("normalizar_descripcion: fallback due to %s: %s", type(exc).__name__, exc)
        return fallback


@tool
def normalizar_descripcion(descripcion: str, tipo_servicio: str) -> dict:
    """
    Normalizes a mechanic's service description: detects the language,
    corrects spelling errors, and translates to English if needed.

    Call this tool BEFORE registrar_servicio whenever the mechanic provides
    a free-text description of the work performed.

    Args:
        descripcion:   Raw description written by the mechanic (Spanish or English,
                       may contain spelling errors).
        tipo_servicio: Type of service being performed (e.g. "Cambio de aceite").

    Returns:
        Dictionary with:
          - idioma: detected language code ("es", "en", or "unknown")
          - descripcion_normalizada: corrected and English description
          - corrections_summary: one-sentence summary of changes made
    """
    return run_normalizacion(descripcion, tipo_servicio)
