"""
app.py — Punto de entrada principal
Bitácora de Seguimiento · Atento
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from utils.auth import require_auth, login_page
from utils.supabase_client import init_session, logout, is_admin

# ── Configuración de página ──────────────────────────────────
st.set_page_config(
    page_title="Bitácora · Atento",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ───────────────────────────────────────────────
st.markdown("""
<style>
/* Paleta Atento */
:root {
    --atento-blue: #1a3c5e;
    --atento-light: #2563a8;
    --atento-accent: #e8f0fe;
    --atento-success: #16a34a;
    --atento-warning: #d97706;
    --atento-danger: #dc2626;
    --atento-neutral: #6b7280;
}

/* Header sidebar */
[data-testid="stSidebar"] {
    background: var(--atento-blue);
}
[data-testid="stSidebar"] * {
    color: white !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 15px;
    padding: 6px 0;
}

/* Chips de calificación */
.chip-positiva { background:#dcfce7; color:#166534; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.chip-neutra   { background:#fef9c3; color:#854d0e; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.chip-negativa { background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }

/* Cards */
.card {
    background: white;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.card-alerta {
    border-left: 4px solid var(--atento-danger);
}
.card-ok {
    border-left: 4px solid var(--atento-success);
}

/* Métricas personalizadas */
.metric-box {
    background: var(--atento-accent);
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.metric-value { font-size: 32px; font-weight: 700; color: var(--atento-blue); }
.metric-label { font-size: 13px; color: var(--atento-neutral); margin-top: 2px; }

/* Ocultar menú hamburguesa */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Auth ─────────────────────────────────────────────────────
init_session()

# login_page() maneja tanto la UI como el callback via ?access_token
if not st.session_state.get("usuario"):
    login_page()
    st.stop()

usuario = st.session_state["usuario"]

# ── Sidebar navegación ───────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:12px 0 20px 0;">
        <div style="font-size:22px;font-weight:700;">📋 Bitácora</div>
        <div style="font-size:12px;opacity:0.75;margin-top:2px;">Atento · Delivery Management</div>
    </div>
    <hr style="border-color:rgba(255,255,255,0.2);margin:0 0 16px 0;">
    <div style="font-size:13px;opacity:0.8;margin-bottom:4px;">👤 {usuario['nombre']} {usuario.get('apellido','')}</div>
    <div style="font-size:11px;opacity:0.6;margin-bottom:20px;">{usuario['rol'].upper()}</div>
    """, unsafe_allow_html=True)

    # Menú
    opciones = {
        "🏠 Dashboard": "dashboard",
        "➕ Nueva Reunión": "nueva_reunion",
        "📚 Bitácora": "bitacora",
        "✅ Pendientes": "pendientes",
        "👥 Contactos": "contactos",
    }
    if is_admin():
        opciones["⚙️ Administración"] = "admin"
    opciones["🔑 Cambiar contraseña"] = "cambiar_password"

    pagina_sel = st.radio(
        "Navegación",
        list(opciones.keys()),
        label_visibility="collapsed"
    )
    pagina = opciones[pagina_sel]

    st.markdown("<hr style='border-color:rgba(255,255,255,0.2);margin:20px 0 12px 0;'>", unsafe_allow_html=True)
    if st.button("🚪 Cerrar sesión", use_container_width=True):
        logout()

# ── Routing de páginas ───────────────────────────────────────
if pagina == "dashboard":
    from modulos import dashboard
    dashboard.show(usuario)

elif pagina == "nueva_reunion":
    from modulos import nueva_reunion
    nueva_reunion.show(usuario)

elif pagina == "bitacora":
    from modulos import bitacora
    bitacora.show(usuario)

elif pagina == "pendientes":
    from modulos import pendientes
    pendientes.show(usuario)

elif pagina == "contactos":
    from modulos import contactos
    contactos.show(usuario)

elif pagina == "admin":
    if is_admin():
        from modulos import admin
        admin.show(usuario)
    else:
        st.error("Acceso denegado.")

elif pagina == "cambiar_password":
    from modulos import cambiar_password
    cambiar_password.show(usuario)
