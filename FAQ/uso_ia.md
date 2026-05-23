# 9. Uso de herramientas de IA en el proyecto 

En este proyecto se utilizaron herramientas de IA como apoyo puntual en tareas de diseño, depuración y documentación. Las herramientas principales fueron GitHub Copilot y Claude CLI, utilizando modelos como Claude Sonnet y Claude Opus. La implementación final, decisiones de arquitectura y validación de resultados fueron responsabilidad del equipo.

| Área | Uso | Herramienta / modelo |
|---|---|---|
| Generación de datos sintéticos (notebook 0) | Apoyo en el diseño del mecanismo de variable latente `health_score ~ Beta(2,3)` y la lógica de correlación con variables operacionales | Claude CLI (Claude Sonnet / Claude Opus) |
| Logs del pipeline | Integración del registro por etapa para reportar descripciones, tiempos de ejecución y conteos de registros procesados | GitHub Copilot (Claude Sonnet) |
| Diseño de datos mockeados | Definición de estructuras y reglas de datos sintéticos para desacoplar el frontend de Streamlit de la capa de persistencia durante desarrollo y pruebas | GitHub Copilot (Claude Sonnet) |
| Interacción visual tipo chat en Streamlit | Apoyo en el diseño del esqueleto visual (layout, componentes y estilos CSS) para exponer la lógica del agente; la implementación final, ajustes funcionales e integración quedaron a cargo del equipo | GitHub Copilot (Claude Sonnet / Claude Opus) |
| Estructura del chatbot (agente + frontend) | Apoyo parcial en la definición de la estructura modular del chatbot, organización de componentes e integración entre la lógica del agente y la interfaz en Streamlit | GitHub Copilot y Claude CLI (Claude Sonnet / Claude Opus) |
| Búsqueda de errores de configuración | Apoyo para identificar y corregir errores de configuración en Makefile, dependencias, despliegue ECS/Fargate y conexión a RDS | GitHub Copilot (Claude Sonnet / Claude Opus) |
| Dudas técnicas y documentación AWS | Apoyo para resolver dudas técnicas y consultar buenas prácticas de servicios AWS (IAM, ECS/Fargate, RDS, CloudFormation y networking) durante el desarrollo y despliegue | GitHub Copilot y Claude CLI (Claude Sonnet / Claude Opus) |
| Revisión de queries SQL | Revisión de consultas para carga inicial de `service_catalog` y lectura de `risk_scores` desde la réplica de lectura | GitHub Copilot (Claude Sonnet) |
| Documentación | Generación del esqueleto de FAQ y README | Claude CLI |
| Docstrings de métodos | Apoyo en la redacción y mejora de docstrings para describir propósito, parámetros, retornos y errores esperados | GitHub Copilot (Claude Sonnet) |
| Diagramas Mermaid notebook 04 | Generación de los diagramas de arquitectura y ERD en formato Mermaid | Claude CLI |
| Simulación de operaciones CRUD | Simulación de operaciones CRUD en maintenance_records notebook 04 | Claude CLI |