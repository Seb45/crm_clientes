"""
utils/auth.py
Autenticación Google OAuth via Supabase + control de sesión única
Estrategia: JS captura el #access_token del fragmento y lo inyecta como query param
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import requests
import uuid
from utils.supabase_client import get_supabase, init_session


def check_and_register_user(google_email: str, google_name: str, auth_uid: str) -> dict | None:
    sb = get_supabase()
    result = sb.table("usuarios_atento").select("*").eq("email", google_email).execute()

    if result.data:
        usuario = result.data[0]
        if not usuario["activo"]:
            return None
        sb.table("usuarios_atento").update({"auth_user_id": auth_uid}).eq("id", usuario["id"]).execute()
        return usuario
    else:
        nombre_parts = google_name.split(" ", 1)
        nuevo = {
            "auth_user_id": auth_uid,
            "email": google_email,
            "nombre": nombre_parts[0],
            "apellido": nombre_parts[1] if len(nombre_parts) > 1 else "",
            "rol": "operador",
            "activo": False,
        }
        sb.table("usuarios_atento").insert(nuevo).execute()
        return None


def invalidate_other_sessions(usuario_id: str, current_session_id: str):
    sb = get_supabase()
    try:
        sb.table("sesiones_activas").upsert({
            "usuario_id": usuario_id,
            "session_id": current_session_id,
            "updated_at": "now()"
        }, on_conflict="usuario_id").execute()
    except Exception:
        pass


def is_session_valid(usuario_id: str, session_id: str) -> bool:
    sb = get_supabase()
    try:
        result = sb.table("sesiones_activas").select("session_id").eq("usuario_id", usuario_id).execute()
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

    # Flujo 2: token capturado por JS y reenviado como query param
    if "access_token" in params:
        _handle_token(params["access_token"])
        return False

    # JS: lee #access_token del fragmento y recarga con ?access_token=...
    supabase_url = st.secrets["SUPABASE_URL"]
    redirect_url = st.secrets.get("REDIRECT_URL", "http://localhost:8501")
    oauth_url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"

    st.markdown("""
        <script>
        (function() {
            var hash = window.location.hash;
            if (hash && hash.includes('access_token')) {
                var params = new URLSearchParams(hash.substring(1));
                var token = params.get('access_token');
                if (token) {
                    window.location.href = window.location.pathname + '?access_token=' + token;
                }
            }
        })();
        </script>
        <style>.block-container { padding-top: 60px !important; }</style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(
            "<div style='text-align:center;padding:40px 32px 32px 32px;"
            "background:#ffffff;border-radius:16px;"
            "box-shadow:0 4px 24px rgba(0,0,0,0.10);'>"
            "<div style='font-size:52px;margin-bottom:8px;'>📋</div>"
            "<div style='font-size:26px;font-weight:700;color:#1a3c5e;margin-bottom:4px;'>Bit\u00e1cora Atento</div>"
            "<div style='font-size:14px;color:#6b7280;margin-bottom:28px;'>Sistema de seguimiento de reuniones</div>"
            "</div>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)
        st.link_button("\U0001f535  Ingresar con Google", oauth_url, use_container_width=True)
        st.markdown(
            "<div style='text-align:center;margin-top:12px;font-size:12px;color:#9ca3af;'>"
            "Ingres\u00e1 con tu cuenta Google personal o de trabajo"
            "</div>",
            unsafe_allow_html=True
        )
    return False


def _handle_token(access_token: str):
    supabase_url = st.secrets["SUPABASE_URL"]
    anon_key = st.secrets["SUPABASE_ANON_KEY"]

    with st.spinner("Iniciando sesión..."):
        try:
            resp = requests.get(
                f"{supabase_url}/auth/v1/user",
                headers={"apikey": anon_key, "Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if resp.status_code != 200:
                st.error("Token inválido o expirado. Por favor ingresá nuevamente.")
                st.query_params.clear()
                st.rerun()
                return

            user_data = resp.json()
            email    = user_data.get("email", "")
            name     = user_data.get("user_metadata", {}).get("full_name", email)
            auth_uid = user_data.get("id", "")

            if not email:
                st.error("No se pudo obtener el email de Google.")
                st.query_params.clear()
                return

            usuario = check_and_register_user(email, name, auth_uid)

            if usuario is None:
                st.warning("\u26a0\ufe0f Tu acceso est\u00e1 pendiente de activaci\u00f3n.")
                st.info(f"Email registrado: **{email}**  \nComunic\u00e1te con el administrador para activar tu cuenta.")
                st.query_params.clear()
                return

            session_id = str(uuid.uuid4())
            invalidate_other_sessions(usuario["id"], session_id)

            st.session_state["usuario"]    = usuario
            st.session_state["auth_token"] = access_token
            st.session_state["session_id"] = session_id

            st.query_params.clear()
            st.rerun()

        except Exception as e:
            st.error(f"Error al iniciar sesión: {str(e)}")
            st.query_params.clear()


def require_auth():
    init_session()
    usuario = st.session_state.get("usuario")

    if not usuario:
        login_page()
        st.stop()

    session_id = st.session_state.get("session_id")
    if session_id and not is_session_valid(usuario["id"], session_id):
        st.warning("\u26a0\ufe0f Tu sesi\u00f3n fue cerrada porque inici\u00f3 sesi\u00f3n desde otro dispositivo.")
        from utils.supabase_client import logout
        logout()
        st.stop()

    return usuario
