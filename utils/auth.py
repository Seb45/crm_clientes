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
            "<img src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAR8AAABgCAYAAAAkVHbtAAAEEklEQVR4nO3d0XHcIBAGYCeTKlyLa3FxriW1pA3nyTOXG/nCScDuwve92mNLiP0PIdC9vAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA6/gRfQCM9/r2/vndz/78/tAHCKHjBXh9e/8cUfSPQuYRAUQEnW6i23C4WvBng+Y7AojZfkUfwEijRhhnXA2L3mED0VIUZi//K9CoIPruuB4dz+ywyRLS7GOZkU9LsWYaCd2LHNlkbRPWVr7TnSnamcWW/XZJ8BCldMe7Utgjiy5T4NyfZ89Jb7iibOfrUeBnii9TsBwRKAK2ipJzPlEBkDF4rhTXikWa8RpxrFyHi1rfkqVT9wqJo/OpHkArntPKSo18sgTATL2LZ9U2jDwv21fOKRM+ozpXy+P3mR17VGddNXRm0oZ9lQif1ot+W7hVOkqWp24+of9Vpf9UViJ8WtwXz5/fHz9aO9D9780qxCyjnJ2DR8jESd/prm6ZiFgL1PI/M+xqHx06M5+mPbOFZVbg7BzqLVI3To+9Wlc72ogAWj14IiZgW8NnRvBc3bO3S2ilve3Kukk0oyrBc/vziOs3Onh6bRTeZclA2vB5pPqcTE+9JpV73CKdLbAZ7TwqeGY9Kc28KfqslOFj3USbHsGTYcJ15GhoxPlFLUxdLYB+Rh/AvV7B8/r2/pl142kWPYujx986e80yrsMauS5txN+NkGrk421/7a6ca/Z2mnVLNupJ2Oj2XWUElCZ8MhXTChf23pmFmhn8bw3WzIWUM56u7iRN+LS4TXwXub9swXOk+jd09JqgXmH0k2LO59mnJNWDJ+PtZa9Xc1Q3+zbv6Heqh0qr8PBZqeN+qXZOq3f2mefX63+tfk1eXoJvu6oV6YpmfX9Y5DaHDHYIk2eVmvN5RvSenuyFleFLC1ecv7NvrF1Y+ETMW1QIhdF6dNre2zlGvgplhSJdVUj49OpgIzcprtZpI0LnjBVHQxybHj7Rq453HP1UCZ5bPUZDlT9AdthilHbOZ5UGjpZhbufqSPLMaKhy/9nlw3Fq+FR6TcYKt16rrd1pHQ1FXbeM67cySzPymb0WY7cL3ersZHKG27LMHxaPPsx2GdHdmxo+R0WfuTGrj35aj/9McGRql0zH8kjUWzWzmj7yWa0Bz7oSbGdejt9zhHJ03EaTY61YN2luu2ZrLZbqo58vkZ+6ldovY4BWar9nhO/tWtVKHWaX4Mlm9U2mW4dP5IWd8W6Zq57t/Le/W7Vwvjvm1h3po49jJdvedrXaoRPcM9L517MBHL2QtoptTvSRUWtGnvkiuyuyb1fZVdW3R86y5UkfGfVdSbPeR1z9cTlsbYW3JH5Z6VwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADgwF+Sn97myDX/ogAAAABJRU5ErkJggg==' style='height:56px;margin-bottom:16px;display:block;margin-left:auto;margin-right:auto;'/>"
            "<div style='font-size:22px;font-weight:700;color:#1a3c5e;margin-bottom:6px;'>Bitácora Atento</div>"
            "<div style='font-size:13px;color:#6b7280;margin-bottom:24px;'>CRM Clientes &nbsp;&middot;&nbsp; SubWIG 1.2</div>"
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
        from utils.notificaciones import notif_login
        notif_login(usuario)
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
