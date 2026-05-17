"""
modulos/nueva_reunion.py
Formulario completo de carga de reunión — v2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
from datetime import date, datetime, time
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
    "➖ Neutra":   "neutra",
    "❌ Negativa": "negativa",
}

# Links de SharePoint por cliente
SHAREPOINT_LINKS = {
    "TMA (Telefónica)": {
        "base": "https://atentoglobal-my.sharepoint.com/:f:/r/personal/scedermas_ar_atento_com/Documents/Bitacora%20Delivery/TMA?csf=1&web=1&e=MEaOAU",
        "reuniones": "https://atentoglobal-my.sharepoint.com/:f:/r/personal/scedermas_ar_atento_com/Documents/Bitacora%20Delivery/TMA/Reuniones?csf=1&web=1&e=MEaOAU",
        "documentos": "https://atentoglobal-my.sharepoint.com/:f:/r/personal/scedermas_ar_atento_com/Documents/Bitacora%20Delivery/TMA/Documentos?csf=1&web=1&e=MEaOAU",
    },
    # Agregar más clientes acá cuando estén disponibles
}

# Programas fijos por cliente (además de los de la BD)
PROGRAMAS_FIJOS = {
    "TMA (Telefónica)": ["B2B Atención", "B2B Ventas", "B2C Atención", "B2C Televentas", "Otros"],
    "Renault":          ["Courtage", "Plan Rombo", "Customer", "Otros"],
}


def show(usuario: dict):
    st.markdown("## ➕ Nueva Reunión")
    st.divider()

    sb = get_supabase()
    usuario_id = usuario["id"]

    clientes = get_clientes_usuario(usuario_id)
    if not clientes:
        st.warning("No tenés clientes asignados. Contactá al administrador.")
        return

    usuarios_atento = sb.table("usuarios_atento")\
        .select("id, nombre, apellido")\
        .eq("activo", True)\
        .order("nombre").execute().data

    if "form_items" not in st.session_state:
        st.session_state.form_items = []
    if "form_adjuntos" not in st.session_state:
        st.session_state.form_adjuntos = []
    if "nuevo_contacto_mode" not in st.session_state:
        st.session_state.nuevo_contacto_mode = False

    # ══════════════════════════════════════════════════════════
    # SECCIÓN 1: Datos generales
    # ══════════════════════════════════════════════════════════
    st.markdown("### 📌 Datos generales")
    col1, col2 = st.columns(2)

    with col1:
        cliente_nombres = [c["nombre"] for c in clientes]
        cliente_sel_nombre = st.selectbox("Cliente *", cliente_nombres)
        cliente_sel = next(c for c in clientes if c["nombre"] == cliente_sel_nombre)

        # Programas: primero fijos por cliente, luego los de la BD
        programa_id  = None
        programa_txt = None  # para clientes con programas fijos (no en BD)

        if cliente_sel_nombre in PROGRAMAS_FIJOS:
            # Programas fijos hardcodeados
            prog_opciones = ["(Sin programa específico)"] + PROGRAMAS_FIJOS[cliente_sel_nombre]
            prog_sel = st.selectbox("Programa", prog_opciones)
            if prog_sel != "(Sin programa específico)":
                programa_txt = prog_sel
                # Buscar si existe en BD, si no ignorar ID
                progs_bd = sb.table("programas").select("*")\
                    .eq("cliente_id", cliente_sel["id"])\
                    .eq("nombre", prog_sel).execute().data
                if progs_bd:
                    programa_id = progs_bd[0]["id"]

        elif cliente_sel.get("tiene_programas"):
            # Programas dinámicos desde BD
            programas = sb.table("programas").select("*")\
                .eq("cliente_id", cliente_sel["id"])\
                .eq("activo", True).execute().data
            if programas:
                prog_nombres = ["(Sin programa específico)"] + [p["nombre"] for p in programas]
                prog_sel = st.selectbox("Programa", prog_nombres)
                if prog_sel != "(Sin programa específico)":
                    programa_id = next(p["id"] for p in programas if p["nombre"] == prog_sel)

        fecha = st.date_input("Fecha de la reunión *", value=date.today(), max_value=date.today())

    with col2:
        tipo_reunion = st.selectbox("Tipo de reunión *", TIPOS_REUNION)

        # Hora: default hora actual
        hora_actual = datetime.now().time().replace(second=0, microsecond=0)
        hora_str = st.time_input("Hora", value=hora_actual)

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

        if st.button("➕ Agregar nuevo contacto del cliente", type="secondary"):
            st.session_state.nuevo_contacto_mode = True

    with col_aten:
        st.markdown("**Asistentes de Atento**")
        usuario_opciones = {
            f"{u['nombre']} {u.get('apellido', '')}".strip(): u["id"]
            for u in usuarios_atento
        }
        mi_nombre = f"{usuario['nombre']} {usuario.get('apellido', '')}".strip()
        default_atento = [mi_nombre] if mi_nombre in usuario_opciones else []

        sel_atento = st.multiselect(
            "Seleccioná integrantes",
            list(usuario_opciones.keys()),
            default=default_atento,
            placeholder="Buscar..."
        )
        asistentes_atento_ids = [usuario_opciones[s] for s in sel_atento]

    if st.session_state.get("nuevo_contacto_mode"):
        _form_nuevo_contacto(cliente_sel["id"], sb)

    # ══════════════════════════════════════════════════════════
    # SECCIÓN 3: Observaciones
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
    _seccion_adjuntos(cliente_sel_nombre)

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

def _form_nuevo_contacto(cliente_id: str, sb):
    with st.expander("✏️ Nuevo contacto del cliente", expanded=True):
        st.markdown("**Datos profesionales**")
        col1, col2, col3 = st.columns(3)
        with col1:
            nc_nombre   = st.text_input("Nombre *",  key="nc_nombre")
            nc_cargo    = st.text_input("Cargo",      key="nc_cargo")
            nc_email    = st.text_input("Email",      key="nc_email")
        with col2:
            nc_apellido = st.text_input("Apellido *", key="nc_apellido")
            nc_area     = st.text_input("Área",       key="nc_area")
            nc_movil    = st.text_input("Móvil",      key="nc_movil")

        st.markdown("**Datos personales (para atención y presentes)**")
        col3, col4 = st.columns(2)
        with col3:
            nc_fnac = st.date_input(
                "Fecha de nacimiento", value=None, key="nc_fnac",
                min_value=date(1930, 1, 1), max_value=date.today()
            )
            nc_localidad = st.text_input("Localidad",  key="nc_localidad")
            nc_intereses = st.text_input("Intereses",  key="nc_intereses")
            nc_hobbies   = st.text_input("Hobbies",    key="nc_hobbies")
        with col4:
            nc_musica   = st.text_input("Música",          key="nc_musica")
            nc_comida   = st.text_input("Comida favorita", key="nc_comida")
            nc_alcohol  = st.text_input("Bebida / alcohol",key="nc_alcohol")
            nc_deportes = st.text_input("Deportes",        key="nc_deportes")

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
                        "cargo": nc_cargo or None, "area": nc_area or None,
                        "email": nc_email or None, "movil": nc_movil or None,
                        "fecha_nacimiento": str(nc_fnac) if nc_fnac else None,
                        "localidad": nc_localidad or None,
                        "intereses": nc_intereses or None,
                        "hobbies": nc_hobbies or None,
                        "musica": nc_musica or None,
                        "comida": nc_comida or None,
                        "bebida_alcohol": nc_alcohol or None,
                        "deportes": nc_deportes or None,
                        "notas_personales": nc_notas or None,
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


# ── Sección items de seguimiento ─────────────────────────────

def _seccion_items():
    TIPOS   = ["pedido", "reclamo", "reconocimiento"]
    ICONOS  = {"pedido": "📌", "reclamo": "⚠️", "reconocimiento": "🏆"}
    ESTADOS = ["pendiente", "en_curso", "resuelto"]

    # Cargar equipo Atento para selector de responsable
    from utils.supabase_client import get_supabase
    sb = get_supabase()
    equipo = sb.table("usuarios_atento").select("nombre, apellido").eq("activo", True).order("nombre").execute().data
    nombres_equipo = [f"{u['nombre']} {u.get('apellido','') or ''}".strip() for u in equipo]

    for i, item in enumerate(st.session_state.form_items):
        with st.container(border=True):
            col1, col2, col3, col5 = st.columns([1.2, 2.5, 1.2, 0.5])
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
            with col5:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"item_del_{i}", help="Eliminar"):
                    st.session_state.form_items.pop(i)
                    st.rerun()

            # Responsables: multiselect del equipo Atento
            resp_actual = [r.strip() for r in (item.get("responsable") or "").split(",") if r.strip() and r.strip() in nombres_equipo]
            resp_sel = st.multiselect(
                "Responsable(s)",
                nombres_equipo,
                default=resp_actual,
                key=f"item_resp_{i}",
                placeholder="Seleccioná uno o más..."
            )
            st.session_state.form_items[i]["responsable"] = ", ".join(resp_sel)

            fc = st.date_input("Fecha compromiso (opcional)", value=None,
                               key=f"item_fc_{i}", min_value=date.today())
            st.session_state.form_items[i]["fecha_compromiso"] = str(fc) if fc else None

    col_a, _ = st.columns([1, 4])
    with col_a:
        if st.button("➕ Agregar item", type="secondary"):
            st.session_state.form_items.append({
                "tipo": "pedido", "descripcion": "",
                "estado": "pendiente", "responsable": "",
                "fecha_compromiso": None,
            })
            st.rerun()


# ── Sección adjuntos ─────────────────────────────────────────

def _seccion_adjuntos(cliente_nombre: str = ""):
    # Mostrar acceso directo a SharePoint si existe para este cliente
    if cliente_nombre in SHAREPOINT_LINKS:
        links_sp = SHAREPOINT_LINKS[cliente_nombre]
        st.markdown(
            f"📁 **Carpeta SharePoint — {cliente_nombre}:** &nbsp;"
            f"[📂 Reuniones]({links_sp['reuniones']}) &nbsp;|&nbsp; "
            f"[📄 Documentos]({links_sp['documentos']})",
            unsafe_allow_html=True
        )
        st.caption("Subí el archivo a SharePoint y pegá el link en el campo de abajo.")
        st.divider()

    st.markdown("**Links (URLs)**")
    links = [a for a in st.session_state.form_adjuntos if a["tipo"] == "link"]
    for adj in links:
        idx = st.session_state.form_adjuntos.index(adj)
        col1, col2, col3 = st.columns([2, 3, 0.5])
        with col1:
            nombre = st.text_input("Etiqueta", value=adj["nombre"], key=f"adj_nombre_{idx}")
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

    st.markdown("**Archivos**")
    st.info("📁 Subí el archivo a la carpeta del cliente en SharePoint y pegá el link arriba. El acceso queda controlado por los permisos de Microsoft 365.")
    st.session_state["pending_files"] = []


# ── Guardar reunión ──────────────────────────────────────────

def _guardar_reunion(sb, usuario_id, cliente_id, programa_id, fecha, hora,
                     tipo_reunion, calificacion, observaciones,
                     asistentes_cliente_ids, asistentes_atento_ids):

    if not cliente_id or not fecha or not tipo_reunion:
        st.error("Completá los campos obligatorios: Cliente, Fecha y Tipo de reunión.")
        return

    with st.spinner("Guardando reunión..."):
        try:
            reunion_data = {
                "cliente_id":      cliente_id,
                "programa_id":     programa_id,
                "fecha":           str(fecha),
                "hora":            str(hora) if hora else None,
                "tipo_reunion":    tipo_reunion,
                "calificacion":    calificacion,
                "observaciones":   observaciones,
                "usuario_carga_id": usuario_id,
            }
            res = sb.table("reuniones").insert(reunion_data).execute()
            if not res.data:
                st.error("Error al guardar la reunión.")
                return
            reunion_id = res.data[0]["id"]

            for c_id in asistentes_cliente_ids:
                sb.table("reunion_asistentes_cliente").insert(
                    {"reunion_id": reunion_id, "contacto_id": c_id}
                ).execute()

            for u_id in asistentes_atento_ids:
                sb.table("reunion_asistentes_atento").insert(
                    {"reunion_id": reunion_id, "usuario_id": u_id}
                ).execute()

            for item in st.session_state.form_items:
                if item.get("descripcion"):
                    sb.table("items_seguimiento").insert({
                        "reunion_id":       reunion_id,
                        "tipo":             item["tipo"],
                        "descripcion":      item["descripcion"],
                        "estado":           item["estado"],
                        "responsable":      item.get("responsable") or None,
                        "fecha_compromiso": item.get("fecha_compromiso"),
                    }).execute()

            for adj in st.session_state.form_adjuntos:
                if adj.get("url"):
                    sb.table("adjuntos").insert({
                        "reunion_id": reunion_id,
                        "tipo":       "link",
                        "nombre":     adj.get("nombre") or adj["url"],
                        "url":        adj["url"],
                    }).execute()

            for f in st.session_state.get("pending_files", []):
                try:
                    import requests as req
                    import urllib.parse
                    file_bytes = f.read()
                    # Limpiar nombre de archivo: reemplazar espacios y chars problemáticos
                    safe_name = f.name.replace(" ", "_")
                    path = f"reuniones/{reunion_id}/{safe_name}"
                    supabase_url = st.secrets["SUPABASE_URL"]
                    service_key  = st.secrets["SUPABASE_SERVICE_KEY"]
                    # Upload via PUT con service key
                    upload_url = f"{supabase_url}/storage/v1/object/adjuntos-reuniones/{path}"
                    headers = {
                        "Authorization": f"Bearer {service_key}",
                        "apikey": service_key,
                        "Content-Type": f.type or "application/octet-stream",
                        "x-upsert": "true",
                    }
                    resp = req.put(upload_url, headers=headers, data=file_bytes, timeout=60)
                    if resp.status_code not in (200, 201):
                        st.warning(f"No se pudo subir {f.name} (status {resp.status_code}): {resp.text[:200]}")
                        continue
                    public_url = f"{supabase_url}/storage/v1/object/public/adjuntos-reuniones/{path}"
                    sb.table("adjuntos").insert({
                        "reunion_id":   reunion_id,
                        "tipo":         "archivo",
                        "nombre":       f.name,
                        "storage_path": path,
                        "url":          public_url,
                    }).execute()
                except Exception as e:
                    st.warning(f"No se pudo subir {f.name}: {e}")

            # Notificación Telegram
            try:
                from utils.notificaciones import notif_nueva_reunion
                cliente_nombre = next((c["nombre"] for c in get_clientes_usuario(usuario_id) if c["id"] == cliente_id), "")
                notif_nueva_reunion(
                    usuario=sb.table("usuarios_atento").select("*").eq("id", usuario_id).execute().data[0],
                    cliente=cliente_nombre,
                    tipo=tipo_reunion,
                    fecha=str(fecha),
                )
            except Exception:
                pass

            # Limpiar estado
            st.session_state.form_items   = []
            st.session_state.form_adjuntos = []
            st.session_state.pending_files = []

            st.success(f"✅ Reunión guardada correctamente.")
            st.balloons()

        except Exception as e:
            st.error(f"Error inesperado: {str(e)}")
