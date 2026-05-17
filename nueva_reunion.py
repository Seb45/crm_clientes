"""
pages/nueva_reunion.py
Formulario completo de carga de reunión
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
from datetime import date, datetime
import uuid
from utils.supabase_client import get_supabase, get_clientes_usuario

TIPOS_REUNION = [
    "Seguimiento operativo mensual",
    "Reunion puntual",
    "Reclamos",
    "Comercial",
    "Interna",
    "Otra",
]

CALIFICACIONES = {
    "✅ Positiva": "positiva",
    "➖ Neutra": "neutra",
    "❌ Negativa": "negativa",
}


def show(usuario: dict):
    st.markdown("## ➕ Nueva Reunión")
    st.divider()

    sb = get_supabase()
    usuario_id = usuario["id"]

    # ── Cargar datos base ────────────────────────────────────
    clientes = get_clientes_usuario(usuario_id)
    if not clientes:
        st.warning("No tenés clientes asignados. Contactá al administrador.")
        return

    usuarios_atento = sb.table("usuarios_atento")\
        .select("id, nombre, apellido")\
        .eq("activo", True)\
        .order("nombre").execute().data

    # ── Estado del formulario ────────────────────────────────
    if "form_items" not in st.session_state:
        st.session_state.form_items = []   # items de seguimiento
    if "form_adjuntos" not in st.session_state:
        st.session_state.form_adjuntos = []
    if "nuevo_contacto_mode" not in st.session_state:
        st.session_state.nuevo_contacto_mode = False

    # ══════════════════════════════════════════════════════════
    # SECCIÓN 1: Datos generales de la reunión
    # ══════════════════════════════════════════════════════════
    st.markdown("### 📌 Datos generales")
    col1, col2 = st.columns(2)

    with col1:
        cliente_nombres = [c["nombre"] for c in clientes]
        cliente_sel_nombre = st.selectbox("Cliente *", cliente_nombres)
        cliente_sel = next(c for c in clientes if c["nombre"] == cliente_sel_nombre)

        # Programa (solo si el cliente tiene programas)
        programa_id = None
        if cliente_sel.get("tiene_programas"):
            programas = sb.table("programas")\
                .select("*")\
                .eq("cliente_id", cliente_sel["id"])\
                .eq("activo", True)\
                .execute().data
            if programas:
                prog_nombres = ["(Sin programa específico)"] + [p["nombre"] for p in programas]
                prog_sel = st.selectbox("Programa", prog_nombres)
                if prog_sel != "(Sin programa específico)":
                    programa_id = next(p["id"] for p in programas if p["nombre"] == prog_sel)

        fecha = st.date_input("Fecha de la reunión *", value=date.today(), max_value=date.today())

    with col2:
        tipo_reunion = st.selectbox("Tipo de reunión *", TIPOS_REUNION)
        hora_str = st.time_input("Hora", value=None)
        calific_label = st.radio(
            "Calificación para Atento *",
            list(CALIFICACIONES.keys()),
            horizontal=True,
            index=1,
        )
        calificacion = CALIFICACIONES[calific_label]

    # ══════════════════════════════════════════════════════════
    # SECCIÓN 2: Asistentes
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 👥 Asistentes")
    col_cli, col_aten = st.columns(2)

    with col_cli:
        st.markdown("**Asistentes del cliente**")

        contactos = sb.table("contactos_cliente")\
            .select("id, nombre, apellido, cargo")\
            .eq("cliente_id", cliente_sel["id"])\
            .eq("activo", True)\
            .order("apellido").execute().data

        contacto_opciones = {
            f"{c['apellido']}, {c['nombre']} ({c.get('cargo') or '—'})": c["id"]
            for c in contactos
        }

        asistentes_cliente_ids = []
        if contacto_opciones:
            sel_contactos = st.multiselect(
                "Seleccioná contactos",
                list(contacto_opciones.keys()),
                placeholder="Buscar contacto..."
            )
            asistentes_cliente_ids = [contacto_opciones[s] for s in sel_contactos]
        else:
            st.info("No hay contactos cargados para este cliente.")

        # Botón para agregar nuevo contacto
        if st.button("➕ Agregar nuevo contacto del cliente", type="secondary"):
            st.session_state.nuevo_contacto_mode = True

    with col_aten:
        st.markdown("**Asistentes de Atento**")
        usuario_opciones = {
            f"{u['nombre']} {u.get('apellido', '')}": u["id"]
            for u in usuarios_atento
        }
        # Pre-seleccionar al usuario actual
        mi_nombre = f"{usuario['nombre']} {usuario.get('apellido', '')}".strip()
        default_atento = [mi_nombre] if mi_nombre in usuario_opciones else []

        sel_atento = st.multiselect(
            "Seleccioná integrantes",
            list(usuario_opciones.keys()),
            default=default_atento,
            placeholder="Buscar..."
        )
        asistentes_atento_ids = [usuario_opciones[s] for s in sel_atento]

    # ── Formulario nuevo contacto (inline) ──────────────────
    nuevo_contacto_id = None
    if st.session_state.get("nuevo_contacto_mode"):
        nuevo_contacto_id = _form_nuevo_contacto(cliente_sel["id"], sb)

    # ══════════════════════════════════════════════════════════
    # SECCIÓN 3: Observaciones y notas
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📝 Notas de la reunión")
    observaciones = st.text_area(
        "Observaciones adicionales",
        height=100,
        placeholder="Contexto general, temas tratados, clima de la reunión..."
    )

    # ══════════════════════════════════════════════════════════
    # SECCIÓN 4: Items de seguimiento
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📋 Items de seguimiento")
    st.caption("Registrá pedidos, reclamos y reconocimientos con su estado y responsable.")

    _seccion_items()

    # ══════════════════════════════════════════════════════════
    # SECCIÓN 5: Adjuntos
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📎 Adjuntos")
    _seccion_adjuntos()

    # ══════════════════════════════════════════════════════════
    # BOTÓN GUARDAR
    # ══════════════════════════════════════════════════════════
    st.markdown("---")
    col_g1, col_g2, col_g3 = st.columns([2, 1, 2])
    with col_g2:
        guardar = st.button("💾 Guardar reunión", type="primary", use_container_width=True)

    if guardar:
        _guardar_reunion(
            sb=sb,
            usuario_id=usuario_id,
            cliente_id=cliente_sel["id"],
            programa_id=programa_id,
            fecha=fecha,
            hora=hora_str,
            tipo_reunion=tipo_reunion,
            calificacion=calificacion,
            observaciones=observaciones,
            asistentes_cliente_ids=asistentes_cliente_ids,
            asistentes_atento_ids=asistentes_atento_ids,
        )


# ── Formulario nuevo contacto ────────────────────────────────

def _form_nuevo_contacto(cliente_id: str, sb) -> str | None:
    with st.expander("✏️ Nuevo contacto del cliente", expanded=True):
        st.markdown("**Datos profesionales**")
        col1, col2, col3 = st.columns(3)
        with col1:
            nc_nombre   = st.text_input("Nombre *", key="nc_nombre")
            nc_cargo    = st.text_input("Cargo", key="nc_cargo")
            nc_email    = st.text_input("Email", key="nc_email")
        with col2:
            nc_apellido = st.text_input("Apellido *", key="nc_apellido")
            nc_area     = st.text_input("Área", key="nc_area")
            nc_movil    = st.text_input("Móvil", key="nc_movil")

        st.markdown("**Datos personales (para atención y presentes)**")
        col3, col4 = st.columns(2)
        with col3:
            nc_fnac     = st.date_input("Fecha de nacimiento", value=None, key="nc_fnac")
            nc_localidad = st.text_input("Localidad", key="nc_localidad")
            nc_intereses = st.text_input("Intereses", key="nc_intereses")
            nc_hobbies  = st.text_input("Hobbies", key="nc_hobbies")
        with col4:
            nc_musica   = st.text_input("Música", key="nc_musica")
            nc_comida   = st.text_input("Comida favorita", key="nc_comida")
            nc_alcohol  = st.text_input("Bebida / alcohol", key="nc_alcohol")
            nc_deportes = st.text_input("Deportes", key="nc_deportes")

        nc_notas = st.text_area("Notas personales adicionales", key="nc_notas", height=60)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("✅ Guardar contacto", type="primary"):
                if not nc_nombre or not nc_apellido:
                    st.error("Nombre y apellido son obligatorios.")
                else:
                    nuevo = {
                        "cliente_id": cliente_id,
                        "nombre": nc_nombre, "apellido": nc_apellido,
                        "cargo": nc_cargo, "area": nc_area,
                        "email": nc_email, "movil": nc_movil,
                        "fecha_nacimiento": str(nc_fnac) if nc_fnac else None,
                        "localidad": nc_localidad, "intereses": nc_intereses,
                        "hobbies": nc_hobbies, "musica": nc_musica,
                        "comida": nc_comida, "bebida_alcohol": nc_alcohol,
                        "deportes": nc_deportes, "notas_personales": nc_notas,
                    }
                    result = sb.table("contactos_cliente").insert(nuevo).execute()
                    if result.data:
                        st.success(f"Contacto {nc_nombre} {nc_apellido} guardado.")
                        st.session_state.nuevo_contacto_mode = False
                        st.rerun()
        with col_b2:
            if st.button("Cancelar"):
                st.session_state.nuevo_contacto_mode = False
                st.rerun()
    return None


# ── Sección items de seguimiento ─────────────────────────────

def _seccion_items():
    TIPOS = ["pedido", "reclamo", "reconocimiento"]
    ICONOS = {"pedido": "📌", "reclamo": "⚠️", "reconocimiento": "🏆"}
    ESTADOS = ["pendiente", "en_curso", "resuelto"]

    # Mostrar items ya agregados
    for i, item in enumerate(st.session_state.form_items):
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([1.2, 2.5, 1.2, 1.5, 0.5])
            with col1:
                tipo = st.selectbox("Tipo", TIPOS, index=TIPOS.index(item["tipo"]),
                                    key=f"item_tipo_{i}",
                                    format_func=lambda t: f"{ICONOS[t]} {t.capitalize()}")
                st.session_state.form_items[i]["tipo"] = tipo
            with col2:
                desc = st.text_input("Descripción", value=item["descripcion"], key=f"item_desc_{i}")
                st.session_state.form_items[i]["descripcion"] = desc
            with col3:
                estado = st.selectbox("Estado", ESTADOS, index=ESTADOS.index(item["estado"]),
                                      key=f"item_estado_{i}",
                                      format_func=lambda e: e.replace("_", " ").capitalize())
                st.session_state.form_items[i]["estado"] = estado
            with col4:
                resp = st.text_input("Responsable", value=item.get("responsable", ""), key=f"item_resp_{i}")
                st.session_state.form_items[i]["responsable"] = resp
            with col5:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"item_del_{i}", help="Eliminar"):
                    st.session_state.form_items.pop(i)
                    st.rerun()

            # Fecha compromiso
            fc = st.date_input("Fecha compromiso (opcional)", value=None,
                                key=f"item_fc_{i}", min_value=date.today())
            st.session_state.form_items[i]["fecha_compromiso"] = str(fc) if fc else None

    # Botón agregar nuevo item
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button("➕ Agregar item", type="secondary"):
            st.session_state.form_items.append({
                "tipo": "pedido",
                "descripcion": "",
                "estado": "pendiente",
                "responsable": "",
                "fecha_compromiso": None,
            })
            st.rerun()


# ── Sección adjuntos ─────────────────────────────────────────

def _seccion_adjuntos():
    # Links
    st.markdown("**Links (URLs)**")
    for i, adj in enumerate(
        [a for a in st.session_state.form_adjuntos if a["tipo"] == "link"]
    ):
        idx = st.session_state.form_adjuntos.index(adj)
        col1, col2, col3 = st.columns([2, 3, 0.5])
        with col1:
            nombre = st.text_input("Nombre/etiqueta", value=adj["nombre"], key=f"adj_nombre_{idx}")
            st.session_state.form_adjuntos[idx]["nombre"] = nombre
        with col2:
            url = st.text_input("URL", value=adj["url"], key=f"adj_url_{idx}")
            st.session_state.form_adjuntos[idx]["url"] = url
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"adj_del_{idx}"):
                st.session_state.form_adjuntos.pop(idx)
                st.rerun()

    if st.button("➕ Agregar link", type="secondary", key="add_link"):
        st.session_state.form_adjuntos.append({"tipo": "link", "nombre": "", "url": "", "storage_path": None})
        st.rerun()

    # Archivos
    st.markdown("**Archivos**")
    uploaded_files = st.file_uploader(
        "Subir archivos (PDF, PPT, Word, imágenes)",
        accept_multiple_files=True,
        type=["pdf", "ppt", "pptx", "doc", "docx", "png", "jpg", "jpeg", "gif"],
        key="file_uploader"
    )
    if uploaded_files:
        st.caption(f"{len(uploaded_files)} archivo(s) listo(s) para subir al guardar.")
        # Se subirán al guardar la reunión
        st.session_state["pending_files"] = uploaded_files
    else:
        st.session_state["pending_files"] = []


# ── Guardar reunión completa ─────────────────────────────────

def _guardar_reunion(sb, usuario_id, cliente_id, programa_id, fecha, hora,
                     tipo_reunion, calificacion, observaciones,
                     asistentes_cliente_ids, asistentes_atento_ids):

    # Validaciones básicas
    if not cliente_id or not fecha or not tipo_reunion:
        st.error("Completá los campos obligatorios: Cliente, Fecha y Tipo de reunión.")
        return

    with st.spinner("Guardando reunión..."):
        try:
            # 1. Insertar reunión
            reunion_data = {
                "cliente_id": cliente_id,
                "programa_id": programa_id,
                "fecha": str(fecha),
                "hora": str(hora) if hora else None,
                "tipo_reunion": tipo_reunion,
                "calificacion": calificacion,
                "observaciones": observaciones,
                "usuario_carga_id": usuario_id,
            }
            res = sb.table("reuniones").insert(reunion_data).execute()
            if not res.data:
                st.error("Error al guardar la reunión.")
                return
            reunion_id = res.data[0]["id"]

            # 2. Asistentes cliente
            for c_id in asistentes_cliente_ids:
                sb.table("reunion_asistentes_cliente").insert({
                    "reunion_id": reunion_id, "contacto_id": c_id
                }).execute()

            # 3. Asistentes Atento
            for u_id in asistentes_atento_ids:
                sb.table("reunion_asistentes_atento").insert({
                    "reunion_id": reunion_id, "usuario_id": u_id
                }).execute()

            # 4. Items de seguimiento
            for item in st.session_state.form_items:
                if item.get("descripcion"):
                    sb.table("items_seguimiento").insert({
                        "reunion_id": reunion_id,
                        "tipo": item["tipo"],
                        "descripcion": item["descripcion"],
                        "estado": item["estado"],
                        "responsable": item.get("responsable") or None,
                        "fecha_compromiso": item.get("fecha_compromiso"),
                    }).execute()

            # 5. Adjuntos links
            for adj in st.session_state.form_adjuntos:
                if adj.get("url"):
                    sb.table("adjuntos").insert({
                        "reunion_id": reunion_id,
                        "tipo": "link",
                        "nombre": adj.get("nombre") or adj["url"],
                        "url": adj["url"],
                    }).execute()

            # 6. Archivos subidos a Supabase Storage
            pending_files = st.session_state.get("pending_files", [])
            for f in pending_files:
                try:
                    file_bytes = f.read()
                    path = f"reuniones/{reunion_id}/{f.name}"
                    sb.storage.from_("adjuntos-reuniones").upload(
                        path, file_bytes,
                        file_options={"content-type": f.type or "application/octet-stream"}
                    )
                    # URL firmada temporal
                    signed = sb.storage.from_("adjuntos-reuniones").create_signed_url(path, 86400)
                    sb.table("adjuntos").insert({
                        "reunion_id": reunion_id,
                        "tipo": "archivo",
                        "nombre": f.name,
                        "storage_path": path,
                        "url": signed.get("signedURL", ""),
                    }).execute()
                except Exception as e:
                    st.warning(f"No se pudo subir el archivo {f.name}: {e}")

            # Limpiar estado
            st.session_state.form_items = []
            st.session_state.form_adjuntos = []
            st.session_state.pending_files = []

            st.success(f"✅ Reunión guardada correctamente (ID: {reunion_id[:8]}...)")
            st.balloons()

        except Exception as e:
            st.error(f"Error inesperado: {str(e)}")
