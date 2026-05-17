"""
utils/auth.py - Autenticación simple usuario/contraseña via Supabase
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import hashlib
import uuid
from utils.supabase_client import get_supabase, init_session


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def login_page():
    init_session()

    if st.session_state.get("usuario"):
        return True

    st.markdown("<style>.block-container{padding-top:60px!important;}</style>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(
            "<div style='text-align:center;padding:40px 32px 24px 32px;"
            "background:#fff;border-radius:16px;"
            "box-shadow:0 4px 24px rgba(0,0,0,0.10);'>"
            "<div style='font-size:52px;margin-bottom:8px;'>📋</div>"
            "<div style='font-size:26px;font-weight:700;color:#1a3c5e;margin-bottom:4px;'>Bitácora Atento</div>"
            "<div style='font-size:14px;color:#6b7280;margin-bottom:24px;'>Sistema de seguimiento de reuniones</div>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            email    = st.text_input("Email", placeholder="tu@email.com")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submit   = st.form_submit_button("Ingresar", use_container_width=True, type="primary")

        if submit:
            if not email or not password:
                st.error("Completá email y contraseña.")
            else:
                _handle_login(email.strip().lower(), password)

    return False


def _handle_login(email: str, password: str):
    sb = get_supabase()
    try:
        result = sb.table("usuarios_atento").select("*").eq("email", email).execute()
        if not result.data:
            st.error("Usuario no encontrado.")
            return

        usuario = result.data[0]

        if not usuario.get("activo"):
            st.warning("Tu cuenta está inactiva. Contactá al administrador.")
            return

        # Verificar contraseña
        password_hash = _hash_password(password)
        if usuario.get("password_hash") != password_hash:
            st.error("Contraseña incorrecta.")
            return

        # Sesión OK
        session_id = str(uuid.uuid4())
        _invalidate_other_sessions(usuario["id"], session_id)

        st.session_state["usuario"]    = usuario
        st.session_state["session_id"] = session_id
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")


def _invalidate_other_sessions(usuario_id: str, session_id: str):
    try:
        get_supabase().table("sesiones_activas").upsert(
            {"usuario_id": usuario_id, "session_id": session_id, "updated_at": "now()"},
            on_conflict="usuario_id"
        ).execute()
    except Exception:
        pass


def is_session_valid(usuario_id: str, session_id: str) -> bool:
    try:
        r = get_supabase().table("sesiones_activas").select("session_id").eq("usuario_id", usuario_id).execute()
        return bool(r.data) and r.data[0]["session_id"] == session_id
    except Exception:
        return True


def require_auth():
    init_session()
    usuario = st.session_state.get("usuario")
    if not usuario:
        login_page()
        st.stop()
    session_id = st.session_state.get("session_id")
    if session_id and not is_session_valid(usuario["id"], session_id):
        st.warning("⚠️ Sesión cerrada por acceso desde otro dispositivo.")
        from utils.supabase_client import logout
        logout()
        st.stop()
    return usuario
