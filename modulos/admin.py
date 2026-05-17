"""
pages/admin.py
Panel de administración: usuarios, roles, permisos por cliente
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
from utils.supabase_client import get_supabase

def show(usuario: dict):
    st.markdown("## ⚙️ Administración")
    st.divider()

    sb = get_supabase()

    tab_usuarios, tab_clientes, tab_equipo = st.tabs([
        "👤 Usuarios y permisos",
        "🏢 Clientes",
        "👥 Equipo Atento",
    ])

    # ══════════════════════════════════════════════════════════
    # TAB 1: USUARIOS
    # ══════════════════════════════════════════════════════════
    with tab_usuarios:
        st.markdown("### Usuarios registrados")
        st.caption("Los usuarios se registran con Google. Activalos aquí y asignales clientes.")

        usuarios = sb.table("usuarios_atento")\
            .select("*").order("nombre").execute().data

        # Separar activos / pendientes
        pendientes = [u for u in usuarios if not u["activo"]]
        activos    = [u for u in usuarios if u["activo"]]

        if pendientes:
            st.markdown("#### 🟡 Pendientes de activación")
            for u in pendientes:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{u['nombre']} {u.get('apellido','')}** · {u['email']}")
                with col2:
                    rol = st.selectbox("Rol", ["operador", "admin"],
                                       key=f"rol_pend_{u['id']}", label_visibility="collapsed")
                with col3:
                    if st.button("✅ Activar", key=f"act_{u['id']}", type="primary"):
                        sb.table("usuarios_atento")\
                            .update({"activo": True, "rol": rol})\
                            .eq("id", u["id"]).execute()
                        # Crear entrada en sesiones_activas (tabla auxiliar)
                        st.success(f"Usuario {u['nombre']} activado.")
                        st.rerun()
            st.divider()

        st.markdown("#### ✅ Usuarios activos")
        todos_clientes = sb.table("clientes").select("id, nombre").eq("activo", True).order("nombre").execute().data

        for u in activos:
            es_yo = u["id"] == usuario["id"]
            label = f"👤 {u['nombre']} {u.get('apellido','')} · {u['email']} · {u['rol']}" + (" (vos)" if es_yo else "")
            with st.expander(label):
                st.markdown("**Datos del usuario**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    ed_nombre   = st.text_input("Nombre",   value=u.get("nombre",""),   key=f"ed_nom_{u['id']}")
                    ed_email    = st.text_input("Email",    value=u.get("email",""),    key=f"ed_email_{u['id']}")
                with col2:
                    ed_apellido = st.text_input("Apellido", value=u.get("apellido",""), key=f"ed_ape_{u['id']}")
                    ed_rol      = st.selectbox("Rol", ["operador","admin"],
                                               index=0 if u.get("rol")=="operador" else 1,
                                               key=f"ed_rol_{u['id']}",
                                               disabled=es_yo)
                with col3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Guardar datos", key=f"save_datos_{u['id']}", type="primary"):
                        sb.table("usuarios_atento").update({
                            "nombre":   ed_nombre,
                            "apellido": ed_apellido,
                            "email":    ed_email.strip().lower(),
                            "rol":      ed_rol,
                        }).eq("id", u["id"]).execute()
                        st.success("Datos actualizados.")
                        st.rerun()

                st.divider()
                col_acc, col_acc2 = st.columns([3, 1])
                with col_acc:
                    st.markdown("**Clientes asignados**")
                    accesos = sb.table("accesos_usuarios").select("cliente_id").eq("usuario_id", u["id"]).execute().data
                    ids_asignados = [a["cliente_id"] for a in accesos]
                    cli_seleccionados = st.multiselect(
                        "Clientes",
                        [c["nombre"] for c in todos_clientes],
                        default=[c["nombre"] for c in todos_clientes if c["id"] in ids_asignados],
                        key=f"clientes_{u['id']}"
                    )
                with col_acc2:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if st.button("💾 Guardar accesos", key=f"save_acc_{u['id']}"):
                        sb.table("accesos_usuarios").delete().eq("usuario_id", u["id"]).execute()
                        for cli_id in [c["id"] for c in todos_clientes if c["nombre"] in cli_seleccionados]:
                            sb.table("accesos_usuarios").insert({"usuario_id": u["id"], "cliente_id": cli_id}).execute()
                        st.success("Accesos actualizados.")
                        st.rerun()

                if not es_yo:
                    st.divider()
                    col_on, _ = st.columns([1, 4])
                    with col_on:
                        lbl = "🔴 Desactivar" if u["activo"] else "🟢 Activar"
                        if st.button(lbl, key=f"toggle_{u['id']}"):
                            sb.table("usuarios_atento").update({"activo": not u["activo"]}).eq("id", u["id"]).execute()
                            st.rerun()

    # ══════════════════════════════════════════════════════════
    # TAB 2: CLIENTES
    # ══════════════════════════════════════════════════════════
    with tab_clientes:
        st.markdown("### Gestión de clientes")

        clientes = sb.table("clientes").select("*").order("nombre").execute().data

        col_lista, col_form = st.columns([2, 1])

        with col_lista:
            for c in clientes:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    estado_icon = "🟢" if c["activo"] else "🔴"
                    prog_icon = " 📂" if c["tiene_programas"] else ""
                    st.markdown(f"{estado_icon} **{c['nombre']}**{prog_icon}")
                with col2:
                    tiene_prog = st.checkbox("Programas", value=c["tiene_programas"],
                                             key=f"prog_{c['id']}", label_visibility="collapsed")
                    if tiene_prog != c["tiene_programas"]:
                        sb.table("clientes").update({"tiene_programas": tiene_prog})\
                            .eq("id", c["id"]).execute()
                        st.rerun()
                with col3:
                    if c["activo"]:
                        if st.button("Ocultar", key=f"hide_cli_{c['id']}"):
                            sb.table("clientes").update({"activo": False})\
                                .eq("id", c["id"]).execute()
                            st.rerun()
                    else:
                        if st.button("Activar", key=f"show_cli_{c['id']}"):
                            sb.table("clientes").update({"activo": True})\
                                .eq("id", c["id"]).execute()
                            st.rerun()
                with col4:
                    if c.get("tiene_programas"):
                        if st.button("Programas", key=f"progs_{c['id']}"):
                            st.session_state["gestion_programas_cliente"] = c["id"]

                # Gestión de programas
                if st.session_state.get("gestion_programas_cliente") == c["id"]:
                    _gestionar_programas(sb, c)

        with col_form:
            st.markdown("**Agregar nuevo cliente**")
            with st.form("form_nuevo_cliente"):
                nuevo_nombre = st.text_input("Nombre del cliente *")
                tiene_prog   = st.checkbox("Tiene programas/subprogramas")
                if st.form_submit_button("➕ Agregar", type="primary"):
                    if nuevo_nombre:
                        sb.table("clientes").insert({
                            "nombre": nuevo_nombre,
                            "tiene_programas": tiene_prog,
                            "activo": True
                        }).execute()
                        st.success(f"Cliente '{nuevo_nombre}' agregado.")
                        st.rerun()
                    else:
                        st.error("El nombre es obligatorio.")

    # ══════════════════════════════════════════════════════════
    # TAB 3: EQUIPO ATENTO
    # ══════════════════════════════════════════════════════════
    with tab_equipo:
        st.markdown("### Miembros del equipo Atento")
        st.caption("Estas son las personas que pueden ser seleccionadas como asistentes en reuniones.")

        equipo = sb.table("usuarios_atento")\
            .select("id, nombre, apellido, email, rol, activo")\
            .order("nombre").execute().data

        # Mostrar tabla
        col_h1, col_h2, col_h3, col_h4 = st.columns([2, 2, 1.5, 1])
        col_h1.markdown("**Nombre**")
        col_h2.markdown("**Email**")
        col_h3.markdown("**Rol**")
        col_h4.markdown("**Estado**")
        st.divider()

        for u in equipo:
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1, 1])
            with col1: st.markdown(f"{u['nombre']} {u.get('apellido','')}")
            with col2: st.markdown(f"`{u['email']}`")
            with col3: st.markdown(f"`{u['rol']}`")
            with col4:
                estado = "🟢 Activo" if u["activo"] else "🔴 Inactivo"
                st.markdown(estado)
            with col5:
                if u["id"] != usuario["id"]:
                    if st.button("🗑️ Eliminar", key=f"del_eq_{u['id']}"):
                        sb.table("accesos_usuarios").delete().eq("usuario_id", u["id"]).execute()
                        sb.table("reunion_asistentes_atento").delete().eq("usuario_id", u["id"]).execute()
                        sb.table("sesiones_activas").delete().eq("usuario_id", u["id"]).execute()
                        sb.table("usuarios_atento").delete().eq("id", u["id"]).execute()
                        st.success(f"{u['nombre']} eliminado.")
                        st.rerun()

        # Agregar miembro manual (sin Google login aún)
        st.divider()
        st.markdown("**Agregar integrante de equipo manualmente**")
        st.caption("Para personas que aún no se loguearon pero deben aparecer como asistentes.")
        with st.form("form_nuevo_miembro"):
            col1, col2 = st.columns(2)
            with col1:
                m_nombre   = st.text_input("Nombre *")
                m_email    = st.text_input("Email (debe ser Gmail) *")
            with col2:
                m_apellido = st.text_input("Apellido")
                m_rol      = st.selectbox("Rol", ["operador", "admin"])

            if st.form_submit_button("➕ Agregar miembro", type="primary"):
                if m_nombre and m_email:
                    sb.table("usuarios_atento").insert({
                        "nombre": m_nombre, "apellido": m_apellido,
                        "email": m_email, "rol": m_rol, "activo": True
                    }).execute()
                    st.success(f"Miembro {m_nombre} agregado.")
                    st.rerun()
                else:
                    st.error("Nombre y email son obligatorios.")


def _gestionar_programas(sb, cliente: dict):
    """UI para gestionar programas de un cliente."""
    with st.container(border=True):
        st.markdown(f"**Programas de {cliente['nombre']}**")
        programas = sb.table("programas").select("*")\
            .eq("cliente_id", cliente["id"]).order("nombre").execute().data

        for p in programas:
            col1, col2 = st.columns([3, 1])
            with col1:
                estado = "🟢" if p["activo"] else "🔴"
                st.markdown(f"{estado} {p['nombre']}")
            with col2:
                if p["activo"]:
                    if st.button("Desactivar", key=f"dprog_{p['id']}"):
                        sb.table("programas").update({"activo": False}).eq("id", p["id"]).execute()
                        st.rerun()
                else:
                    if st.button("Activar", key=f"aprog_{p['id']}"):
                        sb.table("programas").update({"activo": True}).eq("id", p["id"]).execute()
                        st.rerun()

        # Nuevo programa
        with st.form(f"nuevo_prog_{cliente['id']}"):
            nuevo_prog = st.text_input("Nuevo programa")
            if st.form_submit_button("➕ Agregar"):
                if nuevo_prog:
                    sb.table("programas").insert({
                        "cliente_id": cliente["id"], "nombre": nuevo_prog
                    }).execute()
                    st.rerun()

        if st.button("✖ Cerrar", key=f"close_prog_{cliente['id']}"):
            st.session_state.pop("gestion_programas_cliente", None)
            st.rerun()
