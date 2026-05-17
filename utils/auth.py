"""
utils/auth.py
Autenticación Google OAuth via Supabase - flujo PKCE
El code llega como ?code= en la URL, Streamlit lo lee directamente.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import requests
import uuid
import hashlib
import base64
import secrets
from utils.supabase_client import get_supabase, init_session


# ── PKCE helpers ────────────────────────────────────────────

def _generate_code_verifier() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()

def _generate_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()


# ── User management ─────────────────────────────────────────

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
        sb.table("usuarios_atento").insert({
            "auth_user_id": auth_uid,
            "email": google_email,
            "nombre": nombre_parts[0],
            "apellido": nombre_parts[1] if len(nombre_parts) > 1 else "",
            "rol": "operador",
            "activo": False,
        }).execute()
        return None


def invalidate_other_sessions(usuario_id: str, current_session_id: str):
    try:
        get_supabase().table("sesiones_activas").upsert({
            "usuario_id": usuario_id,
            "session_id": current_session_id,
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


# ── Login page ───────────────────────────────────────────────

def login_page():
    init_session()

    if st.session_state.get("usuario"):
        return True

    params = st.query_params

    # ── Flujo PKCE: llegó el ?code= ──────────────────────────
    if "code" in params:
        _handle_pkce_callback(params["code"])
        return False

    # ── Error devuelto por Supabase/Google ───────────────────
    if "error" in params:
        st.error(f"Error de autenticación: {params.get('error_description', params['error'])}")
        if st.button("Reintentar"):
            st.query_params.clear()
            st.rerun()
        return False

    # ── Generar PKCE y URL de login ──────────────────────────
    if "pkce_verifier" not in st.session_state:
        st.session_state["pkce_verifier"] = _generate_code_verifier()

    verifier   = st.session_state["pkce_verifier"]
    challenge  = _generate_code_challenge(verifier)

    supabase_url = st.secrets["SUPABASE_URL"]
    anon_key     = st.secrets["SUPABASE_ANON_KEY"]
    redirect_url = st.secrets.get("REDIRECT_URL", "http://localhost:8501")

    oauth_url = (
        f"{supabase_url}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={redirect_url}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
        f"&response_type=code"
    )

    # ── UI ────────────────────────────────────────────────────
    st.markdown("<style>.block-container{padding-top:60px!important;}</style>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(
            "<div style='text-align:center;padding:40px 32px 32px 32px;"
            "background:#ffffff;border-radius:16px;"
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
            "Ingresá con tu cuenta Google personal o de trabajo"
            "</div>",
            unsafe_allow_html=True
        )
    return False


# ── PKCE callback handler ────────────────────────────────────

def _handle_pkce_callback(code: str):
    supabase_url = st.secrets["SUPABASE_URL"]
    anon_key     = st.secrets["SUPABASE_ANON_KEY"]
    redirect_url = st.secrets.get("REDIRECT_URL", "http://localhost:8501")
    verifier     = st.session_state.get("pkce_verifier", "")

    with st.spinner("Iniciando sesión..."):
        try:
            # Intercambiar code + verifier por tokens
            resp = requests.post(
                f"{supabase_url}/auth/v1/token?grant_type=pkce",
                headers={
                    "apikey": anon_key,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "auth_code": code,
                    "code_verifier": verifier,
                    "redirect_uri": redirect_url,
                },
                timeout=15
            )

            if resp.status_code != 200:
                # Fallback: intentar con JSON body
                resp2 = requests.post(
                    f"{supabase_url}/auth/v1/token?grant_type=pkce",
                    headers={
                        "apikey": anon_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "auth_code": code,
                        "code_verifier": verifier,
                    },
                    timeout=15
                )
                if resp2.status_code == 200:
                    resp = resp2
                else:
                    st.error(f"Error al obtener token ({resp.status_code}): {resp.text[:200]}")
                    st.query_params.clear()
                    return

            token_data = resp.json()

            if "access_token" not in token_data:
                st.error(f"Respuesta inesperada de Supabase: {str(token_data)[:200]}")
                st.query_params.clear()
                return

            access_token = token_data["access_token"]
            user_data    = token_data.get("user", {})
            email        = user_data.get("email", "")
            name         = user_data.get("user_metadata", {}).get("full_name", email)
            auth_uid     = user_data.get("id", "")

            if not email:
                st.error("No se pudo obtener el email de tu cuenta Google.")
                st.query_params.clear()
                return

            usuario = check_and_register_user(email, name, auth_uid)

            if usuario is None:
                st.warning("⚠️ Tu acceso está pendiente de activación.")
                st.info(f"Email registrado: **{email}**  \nContactá al administrador para activar tu cuenta.")
                st.query_params.clear()
                return

            session_id = str(uuid.uuid4())
            invalidate_other_sessions(usuario["id"], session_id)

            st.session_state["usuario"]      = usuario
            st.session_state["auth_token"]   = access_token
            st.session_state["session_id"]   = session_id
            st.session_state.pop("pkce_verifier", None)

            st.query_params.clear()
            st.rerun()

        except Exception as e:
            st.error(f"Error inesperado: {str(e)}")
            st.query_params.clear()


# ── Require auth ─────────────────────────────────────────────

def require_auth():
    init_session()
    usuario = st.session_state.get("usuario")

    if not usuario:
        login_page()
        st.stop()

    session_id = st.session_state.get("session_id")
    if session_id and not is_session_valid(usuario["id"], session_id):
        st.warning("⚠️ Tu sesión fue cerrada porque iniciaste sesión desde otro dispositivo.")
        from utils.supabase_client import logout
        logout()
        st.stop()

    return usuario
