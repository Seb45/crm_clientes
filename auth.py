"""
utils/auth.py
Autenticación Google OAuth via Supabase + control de sesión única
"""

import streamlit as st
import requests
import uuid
from utils.supabase_client import get_supabase, get_supabase_anon, init_session


def check_and_register_user(google_email: str, google_name: str, auth_uid: str) -> dict | None:
    """
    Verifica si el usuario existe en usuarios_atento.
    - Si existe y está activo: retorna sus datos.
    - Si existe pero inactivo: bloquea acceso.
    - Si no existe: crea registro pendiente de activación por admin.
    Retorna dict del usuario o None si no autorizado.
    """
    sb = get_supabase()

    # Buscar usuario existente
    result = sb.table("usuarios_atento")\
        .select("*")\
        .eq("email", google_email)\
        .execute()

    if result.data:
        usuario = result.data[0]
        if not usuario["activo"]:
            return None  # bloqueado
        # Actualizar auth_user_id y last_login si hace falta
        sb.table("usuarios_atento")\
            .update({"auth_user_id": auth_uid, "last_login": "now()"})\
            .eq("id", usuario["id"])\
            .execute()
        return usuario
    else:
        # Primer login: registrar como pendiente (inactivo hasta que admin active)
        nombre_parts = google_name.split(" ", 1)
        nuevo = {
            "auth_user_id": auth_uid,
            "email": google_email,
            "nombre": nombre_parts[0],
            "apellido": nombre_parts[1] if len(nombre_parts) > 1 else "",
            "rol": "operador",
            "activo": False,  # Admin debe activar
        }
        sb.table("usuarios_atento").insert(nuevo).execute()
        return None  # pendiente de aprobación


def invalidate_other_sessions(usuario_id: str, current_session_id: str):
    """
    Registra la sesión activa del usuario.
    Si hay otra sesión, la marca como inválida.
    Usamos la tabla de sesiones activas en Supabase.
    """
    sb = get_supabase()
    # Upsert sesión activa (1 por usuario)
    sb.table("sesiones_activas")\
        .upsert({
            "usuario_id": usuario_id,
            "session_id": current_session_id,
            "updated_at": "now()"
        }, on_conflict="usuario_id")\
        .execute()


def is_session_valid(usuario_id: str, session_id: str) -> bool:
    """Verifica que la sesión actual siga siendo la válida."""
    sb = get_supabase()
    result = sb.table("sesiones_activas")\
        .select("session_id")\
        .eq("usuario_id", usuario_id)\
        .execute()
    if not result.data:
        return False
    return result.data[0]["session_id"] == session_id


def login_page():
    """
    Muestra la pantalla de login con Google OAuth.
    Retorna True si el login fue exitoso.
    """
    init_session()

    # Verificar parámetros OAuth en URL (callback de Google)
    params = st.query_params

    # Si ya hay sesión activa, no mostrar login
    if st.session_state.get("usuario"):
        return True

    # ── UI de login ──────────────────────────────────────────
    st.markdown("""
        <style>
        .login-container {
            max-width: 420px;
            margin: 80px auto 0 auto;
            padding: 40px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.10);
            text-align: center;
        }
        .login-logo {
            font-size: 48px;
            margin-bottom: 8px;
        }
        .login-title {
            font-size: 26px;
            font-weight: 700;
            color: #1a3c5e;
            margin-bottom: 4px;
        }
        .login-subtitle {
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 32px;
        }
        .stButton > button {
            width: 100%;
            background: #ffffff;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 600;
            color: #374151;
            cursor: pointer;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            background: #f9fafb;
            border-color: #1a3c5e;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-logo">📋</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Bitácora Atento</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Sistema de seguimiento de reuniones</div>', unsafe_allow_html=True)

        # Generar URL OAuth de Supabase con Google
        supabase_url = st.secrets["SUPABASE_URL"]
        redirect_url = st.secrets.get("REDIRECT_URL", "http://localhost:8501")
        oauth_url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"

        st.link_button("🔵  Ingresar con Google", oauth_url, use_container_width=True)
        st.markdown('<div style="margin-top:16px;font-size:12px;color:#9ca3af;">Acceso exclusivo con cuenta Google corporativa</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Procesar callback OAuth ──────────────────────────────
    # Supabase redirige con #access_token en el fragment (manejado via JS)
    # Alternativa: usar st.query_params para el code exchange
    if "code" in params:
        _handle_oauth_callback(params["code"])

    return False


def _handle_oauth_callback(code: str):
    """Intercambia el code de OAuth por tokens de Supabase."""
    supabase_url = st.secrets["SUPABASE_URL"]
    anon_key = st.secrets["SUPABASE_ANON_KEY"]
    redirect_url = st.secrets.get("REDIRECT_URL", "http://localhost:8501")

    try:
        resp = requests.post(
            f"{supabase_url}/auth/v1/token?grant_type=pkce",
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"auth_code": code, "redirect_uri": redirect_url},
            timeout=10
        )
        token_data = resp.json()

        if "access_token" not in token_data:
            st.error("Error al procesar el login. Intentá de nuevo.")
            return

        user_data = token_data.get("user", {})
        email = user_data.get("email", "")
        name = user_data.get("user_metadata", {}).get("full_name", email)
        auth_uid = user_data.get("id", "")

        # Verificar/registrar usuario
        usuario = check_and_register_user(email, name, auth_uid)

        if usuario is None:
            st.warning("⚠️ Tu cuenta está pendiente de activación por el administrador.")
            st.info(f"Email registrado: **{email}**. Contactá al admin para que active tu acceso.")
            return

        # Generar session_id único
        session_id = str(uuid.uuid4())

        # Invalidar otras sesiones del mismo usuario
        invalidate_other_sessions(usuario["id"], session_id)

        # Guardar en session_state
        st.session_state["usuario"] = usuario
        st.session_state["auth_token"] = token_data["access_token"]
        st.session_state["session_id"] = session_id

        # Limpiar params de URL
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.error(f"Error de autenticación: {str(e)}")


def require_auth():
    """
    Decorator-like function. Llama al inicio de cada página.
    Si no hay sesión válida, redirige al login.
    """
    init_session()
    usuario = st.session_state.get("usuario")

    if not usuario:
        login_page()
        st.stop()

    # Verificar sesión única (no fue desplazado por otro login)
    session_id = st.session_state.get("session_id")
    if session_id and not is_session_valid(usuario["id"], session_id):
        st.warning("⚠️ Tu sesión fue cerrada porque iniciaste sesión desde otro dispositivo.")
        from utils.supabase_client import logout
        logout()
        st.stop()

    return usuario
