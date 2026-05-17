"""
utils/auth.py - Autenticación via Supabase SDK (flujo implicit con exchange de code)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import uuid
from utils.supabase_client import get_supabase, init_session


def check_and_register_user(email: str, name: str, auth_uid: str) -> dict | None:
    sb = get_supabase()
    result = sb.table("usuarios_atento").select("*").eq("email", email).execute()
    if result.data:
        usuario = result.data[0]
        if not usuario["activo"]:
            return None
        sb.table("usuarios_atento").update({"auth_user_id": auth_uid}).eq("id", usuario["id"]).execute()
        return usuario
    else:
        nombre_parts = name.split(" ", 1)
        sb.table("usuarios_atento").insert({
            "auth_user_id": auth_uid,
            "email": email,
            "nombre": nombre_parts[0],
            "apellido": nombre_parts[1] if len(nombre_parts) > 1 else "",
            "rol": "operador",
            "activo": False,
        }).execute()
        return None


def invalidate_other_sessions(usuario_id: str, session_id: str):
    try:
        get_supabase().table("sesiones_activas").upsert({
            "usuario_id": usuario_id,
            "session_id": session_id,
            "updated_at": "now()"
        }, on_conflict="usuario_id").execute()
    except Exception:
        pass


def is_session_valid(usuario_id: str, session_id: str) -> bool:
    try:
        result = get_supabase().table("sesiones_activas").select("session_id").eq("usuario_id", usuario_id).execute()
        if not result.data:
            return False
        return result.data[0]["session_id"] == session_id
    except Exception:
        return True


def login_page():
    init_session()

    if st.session_state.get("usuario"):
        return True

    params = st.query_params

    # ── Callback: Supabase devolvió ?code= ───────────────────
    if "code" in params:
        _handle_code(params["code"])
        return False

    if "error" in params:
        st.error(f"Error Google: {params.get('error_description', params.get('error', ''))}")
        if st.button("Volver al login"):
            st.query_params.clear()
            st.rerun()
        return False

    # ── UI de login ──────────────────────────────────────────
    supabase_url = st.secrets["SUPABASE_URL"]
    redirect_url = st.secrets.get("REDIRECT_URL", "http://localhost:8501")

    # URL sin PKCE — flujo implicit/code estándar que Supabase maneja internamente
    oauth_url = (
        f"{supabase_url}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={redirect_url}"
    )

    st.markdown("<style>.block-container{padding-top:60px!important;}</style>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(
            "<div style='text-align:center;padding:40px 32px 32px 32px;"
            "background:#fff;border-radius:16px;"
            "box-shadow:0 4px 24px rgba(0,0,0,0.10);'>"
            "<div style='font-size:52px;margin-bottom:8px;'>📋</div>"
            "<div style='font-size:26px;font-weight:700;color:#1a3c5e;margin-bottom:4px;'>Bitácora Atento</div>"
            "<div style='font-size:14px;color:#6b7280;margin-bottom:28px;'>Sistema de seguimiento de reuniones</div>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button("🔵  Ingresar con Google", oauth_url, use_container_width=True)
        st.markdown(
            "<div style='text-align:center;margin-top:12px;font-size:12px;color:#9ca3af;'>"
            "Ingresá con tu cuenta Google personal o de trabajo</div>",
            unsafe_allow_html=True
        )
    return False


def _handle_code(code: str):
    """
    Supabase devuelve ?code= cuando el flujo NO usa PKCE del lado cliente.
    Usamos el SDK de supabase-py para intercambiarlo por una sesión válida.
    """
    from supabase import create_client

    supabase_url = st.secrets["SUPABASE_URL"]
    anon_key     = st.secrets["SUPABASE_ANON_KEY"]

    with st.spinner("Verificando credenciales..."):
        try:
            # Crear cliente anon para el exchange
            sb_anon = create_client(supabase_url, anon_key)

            # El SDK maneja el exchange de code por sesión
            session = sb_anon.auth.exchange_code_for_session({"auth_code": code})

            user  = session.user
            email = user.email or ""
            name  = (user.user_metadata or {}).get("full_name", email)
            uid   = user.id or ""

            if not email:
                st.error("No se pudo obtener el email de Google.")
                st.query_params.clear()
                return

            usuario = check_and_register_user(email, name, uid)

            if usuario is None:
                st.warning("⚠️ Tu acceso está pendiente de activación.")
                st.info(f"Email: **{email}**  \nContactá al administrador.")
                st.query_params.clear()
                return

            session_id = str(uuid.uuid4())
            invalidate_other_sessions(usuario["id"], session_id)

            st.session_state["usuario"]    = usuario
            st.session_state["auth_token"] = session.session.access_token
            st.session_state["session_id"] = session_id

            st.query_params.clear()
            st.rerun()

        except Exception as e:
            err = str(e)
            st.error(f"Error al iniciar sesión: {err}")
            st.query_params.clear()


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
