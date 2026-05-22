"""
FlotaLogix — Plataforma de Gestión de Flota
v2.0
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from config import define_styles_app, render_header
from mock_data import get_fleet_data, get_service_types, get_parts_catalog, get_mechanics
from db import get_write_engine

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FlotaLogix — Gestión de Flota",
    page_icon="🚛",
    layout="wide",
)

define_styles_app()
render_header()

# ─── Load data ────────────────────────────────────────────────────────────────
df_vehicles, df_services = get_fleet_data()

# ─── Color maps ───────────────────────────────────────────────────────────────
RISK_COLORS = {"Alto": "#DC2626", "Medio": "#D97706", "Bajo": "#059669"}

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_gerente, tab_mecanico, tab_historial = st.tabs([
    "🏢  Gerente",
    "🔧  Mecánico",
    "📋  Historial",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GERENTE
# ══════════════════════════════════════════════════════════════════════════════
with tab_gerente:
    df_v = df_vehicles
    df_s = df_services

    # ── KPI bar ───────────────────────────────────────────────────────────────
    total_veh  = len(df_v)
    red_zone   = int((df_v["risk_level"] == "Alto").sum())
    total_cost = df_v["total_maintenance_cost"].sum()
    available  = int((~df_v["maintenance_required"].fillna(False)).sum())
    avail_pct  = round(available / total_veh * 100) if total_veh else 0

    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">🚛 Flota total</div>
                <div class="kpi-value">{total_veh}</div>
                <div class="kpi-sub">{avail_pct}% operativa</div>
            </div>
            <div class="kpi-card danger">
                <div class="kpi-label">🔴 Zona roja</div>
                <div class="kpi-value">{red_zone}</div>
                <div class="kpi-sub">Riesgo alto — requieren atención</div>
            </div>
            <div class="kpi-card success">
                <div class="kpi-label">✅ Disponibles</div>
                <div class="kpi-value">{available:,}</div>
                <div class="kpi-sub">Sin requerir mantenimiento</div>
            </div>
            <div class="kpi-card warning">
                <div class="kpi-label">🔧 Requieren servicio</div>
                <div class="kpi-value">{total_veh - available:,}</div>
                <div class="kpi-sub">Con mantenimiento pendiente</div>
            </div>
            <div class="kpi-card warning">
                <div class="kpi-label">💰 Costo acumulado</div>
                <div class="kpi-value">${total_cost:,.0f}</div>
                <div class="kpi-sub">MXN · mantenimiento total de flota</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Row 1: Mapa de riesgo + Vehículos zona roja ───────────────────────────
    st.markdown(
        '<div class="section-hdr">Mapa de riesgo de flota</div>',
        unsafe_allow_html=True,
    )

    col_map, col_red = st.columns([3, 2], gap="medium")

    with col_map:
        fig_map = px.scatter_mapbox(
            df_v,
            lat="lat",
            lon="lng",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            size="risk_score",
            size_max=20,
            hover_name="plate",
            hover_data={
                "type":       True,
                "brand":      True,
                "risk_score": True,
                "lat":        False,
                "lng":        False,
                "risk_level": False,
            },
            zoom=9.5,
            center={"lat": 19.40, "lon": -99.15},
            mapbox_style="open-street-map",
            labels={"risk_level": "Riesgo"},
            category_orders={"risk_level": ["Alto", "Medio", "Bajo"]},
        )
        fig_map.update_layout(
            height=400,
            margin=dict(l=0, r=0, t=5, b=5),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.06,
                xanchor="left",
                x=0,
                font=dict(size=11),
            ),
        )
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

    with col_red:
        df_red = (
            df_v[df_v["risk_level"] == "Alto"]
            .sort_values("risk_score", ascending=False)
            [["plate", "make_and_model", "type", "risk_score", "total_maintenance_cost"]]
        )
        st.markdown(
            f'<div style="color:var(--red,#DC2626);font-size:0.65rem;font-weight:700;'
            f'letter-spacing:0.09em;text-transform:uppercase;margin-bottom:0.5rem;">'
            f'⚠ {len(df_red)} vehículos en zona roja</div>',
            unsafe_allow_html=True,
        )
        if df_red.empty:
            st.success("Sin vehículos en zona roja.")
        else:
            st.dataframe(
                df_red,
                use_container_width=True,
                hide_index=True,
                height=380,
                column_config={
                    "plate":                  st.column_config.TextColumn("Placa"),
                    "type":                   st.column_config.TextColumn("Tipo"),
                    "risk_score":             st.column_config.NumberColumn("Score", format="%.1f"),
                    "total_maintenance_cost": st.column_config.NumberColumn("Costo MXN", format="$%.0f"),
                },
            )

    # ── Row 2: Costo acumulado + Servicios más frecuentes ─────────────────────
    col_cost, col_freq = st.columns(2, gap="medium")

    with col_cost:
        st.markdown(
            '<div class="section-hdr">Costo acumulado por mes</div>',
            unsafe_allow_html=True,
        )
        df_monthly = (
            df_s.copy()
            .assign(month=lambda x: pd.to_datetime(x["date"]).dt.to_period("M").astype(str))
            .groupby("month", as_index=False)["cost"].sum()
            .rename(columns={"cost": "mensual"})
            .sort_values("month")
        )
        df_monthly["acumulado"] = df_monthly["mensual"].cumsum()

        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=df_monthly["month"],
            y=df_monthly["mensual"],
            name="Mensual",
            marker_color="rgba(249,115,22,0.70)",
        ))
        fig_cost.add_trace(go.Scatter(
            x=df_monthly["month"],
            y=df_monthly["acumulado"],
            name="Acumulado",
            mode="lines+markers",
            line=dict(color="#0F2240", width=2.5),
            marker=dict(size=5),
            yaxis="y2",
        ))
        fig_cost.update_layout(
            height=290,
            margin=dict(l=0, r=10, t=10, b=0),
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend=dict(orientation="h", y=1.12, x=0),
            yaxis=dict(title="MXN mensual", gridcolor="#F1F5F9", tickformat="$,.0f"),
            yaxis2=dict(
                title="MXN acumulado",
                overlaying="y",
                side="right",
                showgrid=False,
                tickformat="$,.0f",
            ),
            xaxis=dict(gridcolor="#F1F5F9", tickangle=-45),
            bargap=0.25,
        )
        st.plotly_chart(fig_cost, use_container_width=True, config={"displayModeBar": False})

    with col_freq:
        st.markdown(
            '<div class="section-hdr">Servicios más frecuentes</div>',
            unsafe_allow_html=True,
        )
        df_freq = (
            df_s.groupby("service_type", as_index=False)
            .agg(count=("service_id", "count"), avg_cost=("cost", "mean"))
            .sort_values("count", ascending=True)
            .tail(10)
        )
        fig_freq = go.Figure(go.Bar(
            x=df_freq["count"],
            y=df_freq["service_type"],
            orientation="h",
            marker_color="#0F2240",
            text=df_freq["count"],
            textposition="outside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Servicios: %{x}<br>"
                "Costo prom: $%{customdata:,.0f}<extra></extra>"
            ),
            customdata=df_freq["avg_cost"],
        ))
        fig_freq.update_layout(
            height=290,
            margin=dict(l=0, r=50, t=10, b=0),
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(title="Número de servicios", gridcolor="#F1F5F9"),
            yaxis=dict(title=""),
        )
        st.plotly_chart(fig_freq, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MECÁNICO
# ══════════════════════════════════════════════════════════════════════════════
with tab_mecanico:
    # ── Session state init ────────────────────────────────────────────────────
    if "mec_step"      not in st.session_state: st.session_state.mec_step      = 0
    if "mec_data"      not in st.session_state: st.session_state.mec_data      = {}
    if "mec_submitted" not in st.session_state: st.session_state.mec_submitted = False

    plates_mec = sorted(df_vehicles["plate"].tolist())

    # ── Step definitions ──────────────────────────────────────────────────────
    STEPS = [
        {
            "key":      "plate",
            "label":    "🚛 Vehículo",
            "question": "¿Cuál es la placa del vehículo que ingresa a taller?",
            "type":     "select",
            "opts":     plates_mec,
        },
        {
            "key":      "service_type",
            "label":    "🔧 Tipo de servicio",
            "question": "¿Qué tipo de servicio se va a realizar?",
            "type":     "select",
            "opts":     get_service_types(),
        },
        {
            "key":      "description",
            "label":    "📝 Descripción",
            "question": "Describe el trabajo realizado o el problema detectado.",
            "type":     "textarea",
        },
        {
            "key":      "parts",
            "label":    "🔩 Refacciones",
            "question": "¿Qué refacciones se utilizaron? (puedes seleccionar varias)",
            "type":     "multiselect",
            "opts":     get_parts_catalog(),
        },
        {
            "key":      "hours",
            "label":    "⏱ Horas trabajadas",
            "question": "¿Cuántas horas de trabajo fueron necesarias?",
            "type":     "number_hours",
        },
        {
            "key":      "cost",
            "label":    "💰 Costo total",
            "question": "¿Cuál es el costo total del servicio? (MXN)",
            "type":     "number_cost",
        },
        {
            "key":      "mechanic",
            "label":    "👷 Mecánico",
            "question": "¿Quién realizó el servicio?",
            "type":     "select",
            "opts":     get_mechanics(),
        },
    ]

    col_chat, col_preview = st.columns([11, 9], gap="large")

    # ── Chat column ───────────────────────────────────────────────────────────
    with col_chat:
        st.markdown("### Registro de servicio")
        st.caption("Responde cada pregunta para registrar el servicio. El resumen se actualiza en tiempo real.")

        current_step = st.session_state.mec_step
        mec_data     = st.session_state.mec_data

        if st.session_state.mec_submitted:
            st.success("✅ Servicio registrado correctamente en el sistema.")
            if st.button("Registrar otro servicio", key="mec_reset", type="primary"):
                st.session_state.mec_step      = 0
                st.session_state.mec_data      = {}
                st.session_state.mec_submitted = False
                st.rerun()

        else:
            # Render completed steps as chat history
            for i in range(current_step):
                step = STEPS[i]
                st.markdown(
                    f'<div class="chat-agent">🤖 {step["question"]}</div>',
                    unsafe_allow_html=True,
                )
                val = mec_data.get(step["key"], "")
                if isinstance(val, list):
                    val_str = ", ".join(val) if val else "—"
                elif step["type"] == "number_cost":
                    val_str = f"${float(val):,.0f} MXN"
                elif step["type"] == "number_hours":
                    val_str = f"{float(val):.1f} hrs"
                else:
                    val_str = str(val)
                st.markdown(
                    f'<div class="chat-user">{val_str}</div>',
                    unsafe_allow_html=True,
                )

            # Current active step
            if current_step < len(STEPS):
                step = STEPS[current_step]

                # Progress
                st.progress(current_step / len(STEPS))
                st.caption(f"Paso {current_step + 1} de {len(STEPS)} — {step['label']}")

                st.markdown(
                    f'<div class="chat-agent">🤖 {step["question"]}</div>',
                    unsafe_allow_html=True,
                )

                with st.form(key=f"mec_form_{current_step}", clear_on_submit=True):
                    stype = step["type"]
                    val   = None

                    if stype == "select":
                        val = st.selectbox(
                            step["label"],
                            step["opts"],
                            label_visibility="collapsed",
                        )
                    elif stype == "textarea":
                        val = st.text_area(
                            step["label"],
                            placeholder="Ej: Se detectó desgaste en pastillas delanteras...",
                            label_visibility="collapsed",
                        )
                    elif stype == "multiselect":
                        val = st.multiselect(
                            step["label"],
                            step["opts"],
                            label_visibility="collapsed",
                        )
                    elif stype == "number_hours":
                        val = st.number_input(
                            step["label"],
                            min_value=0.5,
                            max_value=24.0,
                            value=2.0,
                            step=0.5,
                            label_visibility="collapsed",
                        )
                    elif stype == "number_cost":
                        val = st.number_input(
                            step["label"],
                            min_value=0.0,
                            max_value=500_000.0,
                            value=1_500.0,
                            step=100.0,
                            label_visibility="collapsed",
                        )

                    submitted = st.form_submit_button(
                        "Continuar →",
                        type="primary",
                        use_container_width=True,
                    )

                    if submitted:
                        if stype == "textarea" and (not val or not val.strip()):
                            st.warning("Por favor escribe una descripción antes de continuar.")
                        elif stype == "multiselect" and not val:
                            st.warning("Selecciona al menos una refacción.")
                        else:
                            st.session_state.mec_data[step["key"]] = val
                            st.session_state.mec_step += 1
                            st.rerun()

            else:
                # All steps done — confirm or edit
                st.progress(1.0)
                st.caption(f"Paso {len(STEPS)} de {len(STEPS)} — Confirmación")
                st.markdown(
                    '<div class="chat-agent">🤖 ¡Perfecto! Todos los datos están listos. '
                    '¿Confirmas el registro de este servicio?</div>',
                    unsafe_allow_html=True,
                )
                col_ok, col_edit = st.columns(2)
                with col_ok:
                    if st.button("✅ Confirmar registro", type="primary", use_container_width=True):
                        d = st.session_state.mec_data
                        notas = (
                            f"{d.get('description', '')} | "
                            f"Refacciones: {', '.join(d.get('parts', []))} | "
                            f"{float(d.get('hours', 0)):.1f} hrs | "
                            f"{d.get('mechanic', '')}"
                        )
                        from sqlalchemy import text as _text
                        _error_msg = None
                        try:
                            with get_write_engine().begin() as _conn:
                                _conn.execute(
                                    _text("""
                                        INSERT INTO maintenance_records
                                            (vehicle_id, service_date, common_problem,
                                             solution_used, mechanic_notes, cost, registered_at)
                                        SELECT v.vehicle_id, NOW(), :problem,
                                               :solution, :notes, :cost, NOW()
                                        FROM   vehicles v
                                        WHERE  v.plate = :plate
                                    """),
                                    {
                                        "plate":    d.get("plate"),
                                        "problem":  d.get("service_type"),
                                        "solution": ", ".join(d.get("parts", [])),
                                        "notes":    notas,
                                        "cost":     float(d.get("cost", 0)),
                                    },
                                )
                                result = _conn.execute(
                                    _text("""
                                        UPDATE risk_scores
                                        SET    maintenance_required = FALSE
                                        WHERE  maintenance_required = TRUE
                                          AND  vehicle_id = (
                                            SELECT vehicle_id FROM vehicles WHERE plate = :plate
                                        )
                                    """),
                                    {"plate": d.get("plate")},
                                )
                                _ = result.rowcount  # filas afectadas (0 = ya estaba en FALSE)
                            st.session_state.mec_submitted = True
                            get_fleet_data.clear()
                        except Exception as _e:
                            _error_msg = str(_e)
                        if _error_msg:
                            st.error(f"Error al guardar en RDS: {_error_msg}")
                        else:
                            st.rerun()
                with col_edit:
                    if st.button("✏️ Editar respuestas", use_container_width=True):
                        st.session_state.mec_step = 0
                        st.rerun()

    # ── Preview column ────────────────────────────────────────────────────────
    with col_preview:
        st.markdown("### Resumen del registro")

        # Vehicle card (if plate selected)
        selected_plate = mec_data.get("plate")
        if selected_plate:
            row_v = df_vehicles[df_vehicles["plate"] == selected_plate]
            if not row_v.empty:
                rv         = row_v.iloc[0]
                risk_color = RISK_COLORS.get(rv["risk_level"], "#64748B")
                st.markdown(
                    f'<div style="background:#0F2240;color:#FFF;border-radius:8px;'
                    f'padding:1rem 1.1rem;margin-bottom:1rem;">'
                    f'<div style="font-size:1.2rem;font-weight:900;letter-spacing:-0.02em;">'
                    f'🚛 {rv["plate"]}</div>'
                    f'<div style="font-size:0.8rem;color:rgba(255,255,255,0.65);margin-top:0.1rem;">'
                    f'{rv["brand"]} · {rv["type"]} · {rv["year"]}</div>'
                    f'<div style="margin-top:0.6rem;display:flex;flex-wrap:wrap;gap:0.4rem;">'
                    f'<span style="background:{risk_color}33;color:{risk_color};'
                    f'font-size:0.71rem;padding:0.15rem 0.6rem;border-radius:999px;font-weight:700;">'
                    f'Riesgo {rv["risk_level"]} · {rv["risk_score"]:.0f} pts</span>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Data summary card
        if mec_data:
            rows_html = ""
            for step in STEPS:
                val = mec_data.get(step["key"])
                if val is None:
                    continue
                if isinstance(val, list):
                    val_str = ", ".join(val) if val else "—"
                elif step["type"] == "number_cost":
                    val_str = f"${float(val):,.0f} MXN"
                elif step["type"] == "number_hours":
                    val_str = f"{float(val):.1f} hrs"
                else:
                    val_str = str(val)
                rows_html += (
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
                    f'padding:0.5rem 0;border-bottom:1px solid #E2E8F0;font-size:0.84rem;gap:0.75rem;">'
                    f'<span style="color:#64748B;font-weight:600;white-space:nowrap;">{step["label"]}</span>'
                    f'<span style="color:#0F172A;font-weight:500;text-align:right;'
                    f'word-break:break-word;max-width:62%;">{val_str}</span>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:#FFF;border:1px solid #E2E8F0;border-radius:8px;'
                f'padding:1rem 1.1rem;">{rows_html}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#F8FAFC;border:2px dashed #CBD5E1;border-radius:8px;'
                'padding:2.5rem 1rem;text-align:center;color:#94A3B8;font-size:0.88rem;">'
                '📋<br><br>El resumen del servicio aparecerá aquí<br>conforme captures los datos.'
                '</div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HISTORIAL / REPORTES
# ══════════════════════════════════════════════════════════════════════════════
with tab_historial:
    df_h = df_services.copy()

    st.markdown("### Historial de servicios")

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 1.2, 1.2])

    with col_f1:
        all_plates_h = ["Todas las placas"] + sorted(df_h["plate"].unique().tolist())
        sel_plate_h  = st.selectbox("Placa", all_plates_h, key="hist_plate")

    with col_f2:
        all_stype_h = ["Todos los servicios"] + sorted(df_h["service_type"].unique().tolist())
        sel_stype_h = st.selectbox("Tipo de servicio", all_stype_h, key="hist_stype")

    with col_f3:
        min_date_h    = pd.to_datetime(df_h["date"]).min()
        default_from  = min_date_h.date() if pd.notna(min_date_h) else date.today().replace(month=1, day=1)
        sel_date_from = st.date_input("Desde", value=default_from, key="hist_from")

    with col_f4:
        max_date_h   = pd.to_datetime(df_h["date"]).max()
        default_to   = max_date_h.date() if pd.notna(max_date_h) else date.today()
        sel_date_to  = st.date_input("Hasta", value=default_to, key="hist_to")

    # Apply filters
    df_filtered = df_h.copy()
    if sel_plate_h != "Todas las placas":
        df_filtered = df_filtered[df_filtered["plate"] == sel_plate_h]
    if sel_stype_h != "Todos los servicios":
        df_filtered = df_filtered[df_filtered["service_type"] == sel_stype_h]
    df_filtered = df_filtered[
        (df_filtered["date"] >= sel_date_from) &
        (df_filtered["date"] <= sel_date_to)
    ]

    # ── KPIs ──────────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Servicios encontrados", f"{len(df_filtered):,}")
    c2.metric("Costo total", f"${df_filtered['cost'].sum():,.0f}" if len(df_filtered) else "—")
    c3.metric(
        "Promedio por servicio",
        f"${df_filtered['cost'].mean():,.0f}" if len(df_filtered) else "—",
    )
    c4.metric("Vehículos únicos", f"{df_filtered['plate'].nunique():,}" if len(df_filtered) else "0")

    st.markdown("")

    # ── Table ─────────────────────────────────────────────────────────────────
    if df_filtered.empty:
        st.warning("No hay registros para los filtros seleccionados.")
    else:
        df_display = (
            df_filtered
            .drop(columns=["service_id", "vehicle_id"])
            .sort_values("date", ascending=False)
        )
        df_display["date"] = pd.to_datetime(df_display["date"])

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "plate":        st.column_config.TextColumn("Placa"),
                "brand":        st.column_config.TextColumn("Marca"),
                "type":         st.column_config.TextColumn("Tipo"),
                "date":         st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "service_type": st.column_config.TextColumn("Servicio"),
                "parts_used":   st.column_config.TextColumn("Solución aplicada"),
                "cost":         st.column_config.NumberColumn("Costo MXN", format="$%.0f"),
                "mechanic":     st.column_config.TextColumn("Notas mecánico"),
            },
        )

        # ── Download ──────────────────────────────────────────────────────────
        st.download_button(
            "⬇ Descargar CSV",
            data=df_filtered.to_csv(index=False).encode("utf-8"),
            file_name=f"historial_flota_{date.today()}.csv",
            mime="text/csv",
            type="primary",
        )
