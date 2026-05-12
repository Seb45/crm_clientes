"""
utils/supabase_client.py
Conexión centralizada a Supabase + helpers de autenticación
"""

import streamlit as st
from supabase import create_client, Client
import os

def get_supabase() -> Client:
    """Retorna cliente Supabase (service_role para operaciones backend)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def get_supabase_anon() -> Client:
    """Retorna cliente Supabase con anon key (para OAuth)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


# ============================================================
# GESTIÓN DE SESIÓN
# ============================================================

def init_session():
    """Inicializa variables de sesión."""
    defaults = {
        "usuario": None,        # dict con datos del usuario logueado
        "auth_token": None,     # token OAuth
        "session_id": None,     # ID único de sesión
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_usuario_actual():
    """Retorna el usuario logueado o None."""
    return st.session_state.get("usuario")


def is_admin():
    """Verifica si el usuario actual es admin."""
    u = get_usuario_actual()
    return u is not None and u.get("rol") == "admin"


def is_logged_in():
    """Verifica si hay sesión activa."""
    return get_usuario_actual() is not None


def logout():
    """Cierra sesión limpiando el estado."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================
# HELPERS DE DATOS
# ============================================================

def get_clientes_usuario(usuario_id: str, solo_activos=True):
    """Retorna los clientes a los que tiene acceso el usuario."""
    sb = get_supabase()
    usuario = get_usuario_actual()

    if usuario and usuario.get("rol") == "admin":
        # Admin ve todos los clientes
        q = sb.table("clientes").select("*")
        if solo_activos:
            q = q.eq("activo", True)
        return q.order("nombre").execute().data
    else:
        # Operador: solo sus clientes asignados
        accesos = sb.table("accesos_usuarios")\
            .select("cliente_id")\
            .eq("usuario_id", usuario_id)\
            .execute().data
        ids = [a["cliente_id"] for a in accesos]
        if not ids:
            return []
        q = sb.table("clientes").select("*").in_("id", ids)
        if solo_activos:
            q = q.eq("activo", True)
        return q.order("nombre").execute().data


def get_clientes_sin_reunion_mes(usuario_id: str):
    """Retorna clientes sin reunión registrada en el mes actual."""
    from datetime import date
    sb = get_supabase()

    hoy = date.today()
    primer_dia = hoy.replace(day=1).isoformat()

    clientes = get_clientes_usuario(usuario_id)
    if not clientes:
        return []

    cliente_ids = [c["id"] for c in clientes]

    # Reuniones del mes
    reuniones = sb.table("reuniones")\
        .select("cliente_id")\
        .gte("fecha", primer_dia)\
        .in_("cliente_id", cliente_ids)\
        .execute().data

    ids_con_reunion = {r["cliente_id"] for r in reuniones}
    return [c for c in clientes if c["id"] not in ids_con_reunion]


def get_ultimas_reuniones(usuario_id: str, limit=10):
    """Retorna las últimas N reuniones accesibles al usuario."""
    sb = get_supabase()
    usuario = get_usuario_actual()

    if usuario and usuario.get("rol") == "admin":
        data = sb.table("reuniones")\
            .select("*, clientes(nombre), programas(nombre), usuarios_atento(nombre, apellido)")\
            .order("fecha", desc=True)\
            .order("fecha_registro", desc=True)\
            .limit(limit)\
            .execute().data
    else:
        accesos = sb.table("accesos_usuarios")\
            .select("cliente_id")\
            .eq("usuario_id", usuario_id)\
            .execute().data
        ids = [a["cliente_id"] for a in accesos]
        if not ids:
            return []
        data = sb.table("reuniones")\
            .select("*, clientes(nombre), programas(nombre), usuarios_atento(nombre, apellido)")\
            .in_("cliente_id", ids)\
            .order("fecha", desc=True)\
            .limit(limit)\
            .execute().data

    return data


def get_items_pendientes(usuario_id: str):
    """Retorna items de seguimiento pendientes o en curso."""
    sb = get_supabase()
    usuario = get_usuario_actual()

    if usuario and usuario.get("rol") == "admin":
        data = sb.table("items_seguimiento")\
            .select("*, reuniones(fecha, cliente_id, clientes(nombre))")\
            .in_("estado", ["pendiente", "en_curso"])\
            .order("created_at", desc=True)\
            .execute().data
    else:
        accesos = sb.table("accesos_usuarios")\
            .select("cliente_id")\
            .eq("usuario_id", usuario_id)\
            .execute().data
        ids = [a["cliente_id"] for a in accesos]
        if not ids:
            return []
        # Filtramos en Python por cliente accesible
        reuniones = sb.table("reuniones")\
            .select("id")\
            .in_("cliente_id", ids)\
            .execute().data
        r_ids = [r["id"] for r in reuniones]
        if not r_ids:
            return []
        data = sb.table("items_seguimiento")\
            .select("*, reuniones(fecha, cliente_id, clientes(nombre))")\
            .in_("reunion_id", r_ids)\
            .in_("estado", ["pendiente", "en_curso"])\
            .order("created_at", desc=True)\
            .execute().data

    return data
