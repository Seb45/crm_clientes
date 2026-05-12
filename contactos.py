"""
pages/contactos.py
ABM de contactos de clientes con datos relacionales
"""

import streamlit as st
from datetime import date
from utils.supabase_client import get_supabase, get_clientes_usuario


def show(usuario: dict):
    st.markdown("## 👥 Contactos de Clientes")
    st.divider()

    sb = get_supabase()
    usuario_id = usuario["id"]
    clientes = get_clientes_usuario(usuario_id)

    if not clientes:
        st.info("No tenés clientes asignados.")
        return

    # ── Tabs principales ─────────────────────────────────────
    tab_lista, tab_nuevo = st.tabs(["📋 Directorio", "➕ Nuevo contacto"])

    # ══════════════════════════════════════════════════════════
    # TAB 1: DIRECTORIO
    # ══════════════════════════════════════════════════════════
    with tab_lista:
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            opciones_cli = ["Todos"] + [c["nombre"] for c in clientes]
            filtro_cliente = st.selectbox("Cliente", opciones_cli, key="cont_cli")
        with col2:
            filtro_busq = st.text_input("Buscar nombre / cargo", placeholder="Escribí para buscar...")
        with col3:
            filtro_activo = st.radio("Estado", ["Activos", "Todos"], horizontal=True, key="cont_act")

        # Construir query
        if filtro_cliente != "Todos":
            cliente_obj = next((c for c in clientes if c["nombre"] == filtro_cliente), None)
            if cliente_obj:
                q = sb.table("contactos_cliente").select("*, clientes(nombre)")\
                    .eq("cliente_id", cliente_obj["id"])
            else:
                q = sb.table("contactos_cliente").select("*, clientes(nombre)")
        else:
            ids_cli = [c["id"] for c in clientes]
            q = sb.table("contactos_cliente").select("*, clientes(nombre)").in_("cliente_id", ids_cli)

        if filtro_activo == "Activos":
            q = q.eq("activo", True)

        contactos = q.order("apellido").execute().data

        # Filtro texto en Python
        if filtro_busq:
            term = filtro_busq.lower()
            contactos = [c for c in contactos if
                         term in (c.get("nombre") or "").lower() or
                         term in (c.get("apellido") or "").lower() or
                         term in (c.get("cargo") or "").lower() or
                         term in (c.get("area") or "").lower()]

        st.markdown(f"**{len(contactos)} contacto(s) encontrado(s)**")

        if not contactos:
            st.info("No hay contactos con esos filtros.")
        else:
            for c in contactos:
                cliente_nombre = (c.get("clientes") or {}).get("nombre", "—")
                _card_contacto(sb, c, cliente_nombre)

    # ══════════════════════════════════════════════════════════
    # TAB 2: NUEVO CONTACTO
    # ══════════════════════════════════════════════════════════
    with tab_nuevo:
        _form_contacto(sb, clientes, contacto_existente=None)


def _card_contacto(sb, c: dict, cliente_nombre: str):
    """Tarjeta expandible de un contacto."""
    nombre_completo = f"{c.get('nombre', '')} {c.get('apellido', '')}".strip()
    cargo = c.get("cargo") or "—"
    area  = c.get("area") or "—"

    with st.expander(f"👤 {nombre_completo} · {cargo} · {cliente_nombre}"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Datos profesionales**")
            st.markdown(f"🏢 **Cliente:** {cliente_nombre}")
            st.markdown(f"💼 **Cargo:** {cargo}")
            st.markdown(f"📂 **Área:** {area}")
            st.markdown(f"📧 **Email:** {c.get('email') or '—'}")
            st.markdown(f"📱 **Móvil:** {c.get('movil') or '—'}")

            st.markdown("**Datos personales**")
            if c.get("fecha_nacimiento"):
                fnac = c["fecha_nacimiento"]
                # Calcular edad y próx. cumple
                try:
                    fnac_date = date.fromisoformat(fnac)
                    edad = (date.today() - fnac_date).days // 365
                    proxim = fnac_date.replace(year=date.today().year)
                    if proxim < date.today():
                        proxim = proxim.replace(year=date.today().year + 1)
                    dias = (proxim - date.today()).days
                    cumple_txt = f"🎂 **Nac.:** {fnac} ({edad} años) — próximo cumple en {dias} días"
                    if dias <= 30:
                        st.warning(cumple_txt)
                    else:
                        st.markdown(cumple_txt)
                except Exception:
                    st.markdown(f"🎂 **Nac.:** {fnac}")
            st.markdown(f"📍 **Localidad:** {c.get('localidad') or '—'}")

        with col2:
            st.markdown("**Intereses y preferencias**")
            campos = [
                ("🎵", "Música", "musica"),
                ("🍽️", "Comida", "comida"),
                ("🍷", "Bebida/Alcohol", "bebida_alcohol"),
                ("⚽", "Deportes", "deportes"),
                ("🎯", "Hobbies", "hobbies"),
                ("💡", "Intereses", "intereses"),
            ]
            for icono, label, campo in campos:
                val = c.get(campo) or "—"
                st.markdown(f"{icono} **{label}:** {val}")

            if c.get("notas_personales"):
                st.markdown(f"📝 **Notas:** {c['notas_personales']}")

        # Botones de acción
        col_e, col_i, _ = st.columns([1, 1, 3])
        with col_e:
            if st.button("✏️ Editar", key=f"edit_cont_{c['id']}"):
                st.session_state[f"editando_contacto_{c['id']}"] = True
                st.rerun()
        with col_i:
            estado_txt = "🔴 Inactivar" if c.get("activo") else "🟢 Reactivar"
            if st.button(estado_txt, key=f"toggle_{c['id']}"):
                sb.table("contactos_cliente").update({"activo": not c.get("activo", True)})\
                    .eq("id", c["id"]).execute()
                st.rerun()

        # Formulario de edición inline
        if st.session_state.get(f"editando_contacto_{c['id']}"):
            st.divider()
            st.markdown("**✏️ Editar contacto**")
            _form_contacto(sb, [], contacto_existente=c)


def _form_contacto(sb, clientes: list, contacto_existente: dict | None):
    """Formulario de alta o edición de contacto."""
    es_edicion = contacto_existente is not None
    c = contacto_existente or {}

    with st.form(key=f"form_contacto_{c.get('id', 'nuevo')}"):
        st.markdown("**Datos profesionales**")
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre   = st.text_input("Nombre *", value=c.get("nombre", ""))
            cargo    = st.text_input("Cargo", value=c.get("cargo", "") or "")
            email    = st.text_input("Email", value=c.get("email", "") or "")
        with col2:
            apellido = st.text_input("Apellido *", value=c.get("apellido", ""))
            area     = st.text_input("Área", value=c.get("area", "") or "")
            movil    = st.text_input("Móvil", value=c.get("movil", "") or "")
        with col3:
            if not es_edicion and clientes:
                cli_nombres = [cl["nombre"] for cl in clientes]
                cli_sel_nombre = st.selectbox("Cliente *", cli_nombres)
                cliente_id = next(cl["id"] for cl in clientes if cl["nombre"] == cli_sel_nombre)
            else:
                st.markdown(f"**Cliente:** {(c.get('clientes') or {}).get('nombre', '—')}")
                cliente_id = c.get("cliente_id")

        st.markdown("**Datos personales**")
        col3, col4 = st.columns(2)
        with col3:
            try:
                fnac_default = date.fromisoformat(c["fecha_nacimiento"]) if c.get("fecha_nacimiento") else None
            except Exception:
                fnac_default = None
            fnac        = st.date_input("Fecha de nacimiento", value=fnac_default)
            localidad   = st.text_input("Localidad", value=c.get("localidad", "") or "")
            intereses   = st.text_input("Intereses", value=c.get("intereses", "") or "")
            hobbies     = st.text_input("Hobbies", value=c.get("hobbies", "") or "")
        with col4:
            musica      = st.text_input("Música", value=c.get("musica", "") or "")
            comida      = st.text_input("Comida favorita", value=c.get("comida", "") or "")
            alcohol     = st.text_input("Bebida / alcohol", value=c.get("bebida_alcohol", "") or "")
            deportes    = st.text_input("Deportes", value=c.get("deportes", "") or "")

        notas = st.text_area("Notas personales adicionales",
                              value=c.get("notas_personales", "") or "", height=70)

        col_b1, col_b2 = st.columns([1, 3])
        with col_b1:
            submitted = st.form_submit_button(
                "💾 Guardar cambios" if es_edicion else "✅ Crear contacto",
                type="primary", use_container_width=True
            )
        with col_b2:
            if es_edicion:
                cancelar = st.form_submit_button("Cancelar", use_container_width=False)
                if cancelar:
                    st.session_state.pop(f"editando_contacto_{c.get('id')}", None)
                    st.rerun()

        if submitted:
            if not nombre or not apellido:
                st.error("Nombre y apellido son obligatorios.")
            elif not es_edicion and not cliente_id:
                st.error("Seleccioná un cliente.")
            else:
                datos = {
                    "nombre": nombre, "apellido": apellido,
                    "cargo": cargo or None, "area": area or None,
                    "email": email or None, "movil": movil or None,
                    "fecha_nacimiento": str(fnac) if fnac else None,
                    "localidad": localidad or None, "intereses": intereses or None,
                    "hobbies": hobbies or None, "musica": musica or None,
                    "comida": comida or None, "bebida_alcohol": alcohol or None,
                    "deportes": deportes or None, "notas_personales": notas or None,
                }
                if es_edicion:
                    sb.table("contactos_cliente").update(datos).eq("id", c["id"]).execute()
                    st.session_state.pop(f"editando_contacto_{c.get('id')}", None)
                    st.success("✅ Contacto actualizado.")
                else:
                    datos["cliente_id"] = cliente_id
                    sb.table("contactos_cliente").insert(datos).execute()
                    st.success(f"✅ Contacto {nombre} {apellido} creado.")
                st.rerun()
