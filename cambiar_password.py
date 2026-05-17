"""
modulos/cambiar_password.py
Cambio de contraseña — propio para cualquier usuario, reset para admin
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import hashlib
from utils.supabase_client import get_supabase


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def show(usuario: dict):
    st.markdown("## 🔑 Cambiar contraseña")
    st.divider()

    es_admin = usuario.get("rol") == "admin"

    if es_admin:
        tab_propia, tab_reset = st.tabs(["🔒 Mi contraseña", "🔧 Resetear contraseña de otro usuario"])
    else:
        tab_propia = st.container()
        tab_reset  = None

    # ══════════════════════════════════════════════════════════
    # TAB / SECCIÓN: MI CONTRASEÑA
    # ══════════════════════════════════════════════════════════
    with tab_propia:
        st.markdown("### Cambiá tu contraseña")
        st.caption("La nueva contraseña debe tener al menos 8 caracteres.")

        with st.form("form_cambiar_pwd"):
            actual    = st.text_input("Contraseña actual",   type="password", placeholder="••••••••")
            nueva     = st.text_input("Nueva contraseña",    type="password", placeholder="••••••••")
            confirmar = st.text_input("Confirmar contraseña",type="password", placeholder="••••••••")

            submitted = st.form_submit_button("💾 Guardar nueva contraseña", type="primary")

        if submitted:
            sb = get_supabase()

            # Validaciones
            if not actual or not nueva or not confirmar:
                st.error("Completá todos los campos.")
            elif len(nueva) < 8:
                st.error("La nueva contraseña debe tener al menos 8 caracteres.")
            elif nueva != confirmar:
                st.error("Las contraseñas no coinciden.")
            else:
                # Verificar contraseña actual
                result = sb.table("usuarios_atento")\
                    .select("password_hash")\
                    .eq("id", usuario["id"])\
                    .execute()

                if not result.data:
                    st.error("Error al verificar usuario.")
                elif result.data[0]["password_hash"] != _hash(actual):
                    st.error("La contraseña actual es incorrecta.")
                elif nueva == actual:
                    st.warning("La nueva contraseña debe ser diferente a la actual.")
                else:
                    sb.table("usuarios_atento")\
                        .update({"password_hash": _hash(nueva)})\
                        .eq("id", usuario["id"])\
                        .execute()
                    st.success("✅ Contraseña actualizada correctamente.")

    # ══════════════════════════════════════════════════════════
    # TAB: RESET CONTRASEÑA (solo admin)
    # ══════════════════════════════════════════════════════════
    if es_admin and tab_reset:
        with tab_reset:
            st.markdown("### Resetear contraseña de un usuario")
            st.caption("Como admin podés establecer una contraseña temporal para cualquier usuario. El usuario deberá cambiarla al ingresar.")

            sb = get_supabase()
            usuarios = sb.table("usuarios_atento")\
                .select("id, nombre, apellido, email, rol")\
                .eq("activo", True)\
                .neq("id", usuario["id"])\
                .order("nombre").execute().data

            if not usuarios:
                st.info("No hay otros usuarios activos.")
            else:
                with st.form("form_reset_pwd"):
                    usuario_opciones = {
                        f"{u['nombre']} {u.get('apellido','')} ({u['email']})": u["id"]
                        for u in usuarios
                    }
                    usuario_sel = st.selectbox(
                        "Seleccioná el usuario",
                        list(usuario_opciones.keys())
                    )
                    nueva_temp   = st.text_input("Nueva contraseña temporal", type="password", placeholder="Mínimo 8 caracteres")
                    confirmar_t  = st.text_input("Confirmar contraseña",      type="password", placeholder="••••••••")

                    submitted_r = st.form_submit_button("🔧 Resetear contraseña", type="primary")

                if submitted_r:
                    if not nueva_temp or not confirmar_t:
                        st.error("Completá todos los campos.")
                    elif len(nueva_temp) < 8:
                        st.error("La contraseña debe tener al menos 8 caracteres.")
                    elif nueva_temp != confirmar_t:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        usuario_id = usuario_opciones[usuario_sel]
                        sb.table("usuarios_atento")\
                            .update({"password_hash": _hash(nueva_temp)})\
                            .eq("id", usuario_id)\
                            .execute()
                        nombre_sel = usuario_sel.split(" (")[0]
                        st.success(f"✅ Contraseña de **{nombre_sel}** reseteada correctamente.")
                        st.info(f"Comunicale la nueva contraseña: `{nueva_temp}`")
