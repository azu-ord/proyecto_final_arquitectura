"""FlotaLogix — Logistics theme styles."""

import streamlit as st
from datetime import date


def define_styles_app() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        :root {
            --navy:          #0F2240;
            --navy-light:    #1A3358;
            --navy-soft:     rgba(15,34,64,0.06);
            --orange:        #F97316;
            --orange-dark:   #EA6C0A;
            --orange-light:  rgba(249,115,22,0.12);
            --red:           #DC2626;
            --red-light:     rgba(220,38,38,0.10);
            --amber:         #D97706;
            --amber-light:   rgba(217,119,6,0.10);
            --green:         #059669;
            --green-light:   rgba(5,150,105,0.10);
            --bg:            #F1F5F9;
            --surface:       #FFFFFF;
            --border:        #CBD5E1;
            --text:          #0F172A;
            --muted:         #64748B;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: var(--text);
            background-color: var(--bg);
        }

        .stApp { background-color: var(--bg); }

        .block-container {
            padding-top: 0 !important;
            padding-bottom: 2rem;
            max-width: 100%;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        div[data-testid="stAppViewBlockContainer"],
        div[data-testid="stMainBlockContainer"] {
            padding-top: 0 !important;
        }

        h1 { font-weight: 900; letter-spacing: -0.04em; color: var(--text); }
        h2 { font-weight: 800; letter-spacing: -0.03em; color: var(--text); }
        h3 { font-weight: 700; color: var(--text); margin-top: 0.5rem; }

        /* ── Top header ──────────────────────────────────────────── */
        .lx-header {
            background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%);
            color: #FFF;
            padding: 0.9rem 1.4rem;
            margin: -1rem -1rem 0 -1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 3px solid var(--orange);
        }

        .lx-logo {
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: -0.05em;
            color: #FFF;
            line-height: 1;
        }

        .lx-logo span { color: var(--orange); }

        .lx-tagline {
            font-size: 0.76rem;
            color: rgba(255,255,255,0.65);
            margin-top: 0.15rem;
            font-weight: 500;
        }

        .lx-meta {
            font-size: 0.8rem;
            color: rgba(255,255,255,0.55);
            text-align: right;
            line-height: 1.6;
        }

        /* ── KPI grid ────────────────────────────────────────────── */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.75rem;
            margin: 1.1rem 0 0.5rem;
        }

        .kpi-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 4px solid var(--orange);
            border-radius: 6px;
            padding: 0.9rem 1.1rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }

        .kpi-card.danger  { border-left-color: var(--red);   }
        .kpi-card.warning { border-left-color: var(--amber); }
        .kpi-card.success { border-left-color: var(--green); }

        .kpi-label {
            color: var(--muted);
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }

        .kpi-value {
            font-size: 1.65rem;
            font-weight: 900;
            letter-spacing: -0.03em;
            color: var(--text);
            line-height: 1.1;
        }

        .kpi-sub {
            font-size: 0.7rem;
            color: var(--muted);
            margin-top: 0.18rem;
        }

        /* ── Section label ───────────────────────────────────────── */
        .section-hdr {
            color: var(--muted);
            font-size: 0.62rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin: 1.3rem 0 0.55rem;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .section-hdr::after {
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border);
        }

        /* ── Risk badges ─────────────────────────────────────────── */
        .badge-alto  { background:var(--red-light);   color:var(--red);   padding:0.18rem 0.55rem; border-radius:999px; font-size:0.71rem; font-weight:700; white-space:nowrap; }
        .badge-medio { background:var(--amber-light);  color:var(--amber); padding:0.18rem 0.55rem; border-radius:999px; font-size:0.71rem; font-weight:700; white-space:nowrap; }
        .badge-bajo  { background:var(--green-light);  color:var(--green); padding:0.18rem 0.55rem; border-radius:999px; font-size:0.71rem; font-weight:700; white-space:nowrap; }

        /* ── Chat bubbles (Mecánico) ──────────────────────────────── */
        .chat-agent {
            background: var(--navy);
            color: #FFF;
            border-radius: 4px 14px 14px 14px;
            padding: 0.75rem 1rem;
            font-size: 0.88rem;
            max-width: 88%;
            margin-bottom: 0.4rem;
            line-height: 1.5;
        }

        .chat-user {
            background: var(--orange-light);
            border: 1px solid rgba(249,115,22,0.35);
            color: var(--text);
            border-radius: 14px 4px 14px 14px;
            padding: 0.75rem 1rem;
            font-size: 0.88rem;
            max-width: 88%;
            margin-left: auto;
            margin-bottom: 0.6rem;
            text-align: right;
            font-weight: 500;
        }

        /* ── Tabs ────────────────────────────────────────────────── */
        div[data-baseweb="tab-list"] {
            border-bottom: 2px solid var(--border);
            margin-bottom: 0;
            gap: 0;
        }

        button[data-baseweb="tab"] {
            font-weight: 700;
            font-size: 0.88rem;
            padding: 0.85rem 1.4rem;
            border-bottom: 3px solid transparent;
            color: var(--muted);
        }

        button[data-baseweb="tab"]:hover {
            color: var(--navy);
            background: var(--bg);
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--navy);
            border-bottom: 3px solid var(--orange);
            background: transparent;
        }

        /* ── Metrics ──────────────────────────────────────────────── */
        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-top: 3px solid var(--orange);
            border-radius: 6px;
            padding: 0.85rem 1rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        }

        div[data-testid="stMetricValue"] {
            color: var(--navy);
            font-weight: 900;
        }

        div[data-testid="stMetricLabel"] {
            color: var(--muted);
            font-weight: 600;
        }

        /* ── Buttons ──────────────────────────────────────────────── */
        .stButton > button {
            background: var(--navy);
            color: #FFF;
            border: none;
            border-radius: 5px;
            font-weight: 700;
            letter-spacing: 0.01em;
            transition: background 0.2s;
        }

        .stButton > button:hover {
            background: var(--navy-light);
            color: #FFF;
            border: none;
        }

        .stButton > button[kind="primary"] {
            background: var(--orange);
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--orange-dark);
            color: #FFF;
        }

        /* ── Inputs ───────────────────────────────────────────────── */
        div[data-baseweb="select"] > div {
            border: 1px solid var(--border);
            border-radius: 5px;
            background: var(--surface);
        }

        div[data-baseweb="select"] > div:focus-within {
            border-color: var(--orange);
            box-shadow: 0 0 0 1px var(--orange);
        }

        /* ── Dataframe ────────────────────────────────────────────── */
        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 6px;
            overflow: hidden;
        }

        /* ── Alerts ───────────────────────────────────────────────── */
        div[data-testid="stAlert"] {
            border-radius: 5px;
        }

        /* ── Hide Streamlit chrome ────────────────────────────────── */
        #MainMenu, footer, header[data-testid="stHeader"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    today = date.today().strftime("%d %b %Y")
    st.markdown(
        f"""
        <div class="lx-header">
            <div>
                <div class="lx-logo">Flota<span>Logix</span></div>
                <div class="lx-tagline">Gestión Inteligente de Flota · Panel de Control Operativo</div>
            </div>
            <div class="lx-meta">
                {today}<br>
                <span style="font-size:0.7rem;">Turno: 07:00 – 19:00 h</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
