"""
pages/bitacora.py
Listado, búsqueda y detalle de reuniones
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.supabase_client import get_supabase, get_clientes_usuario

CALIFICACION_HTML = {
    "positiva": '<span class="chip-positiva">✅ Positiva</span>',
    "neutra":   '<span class="chip-neutra">➖ Neutra</span>',
    "negativa": '<span class="chip-negativa">❌ Negativa</span>',
}

ESTADO_HTML = {
    "pendiente": "🔴 Pendiente",
    "en_curso":  "🟡 En curso",
    "resuelto":  "🟢 Resuelto",
}

TIPO_ICONO = {
    "pedido": "📌",
    "reclamo": "⚠️",
    "reconocimiento": "🏆",
}


def show(usuario: dict):
    st.markdown("## 📚 Bitácora de Reuniones")
    st.divider()

    sb = get_supabase()
    usuario_id = usuario["id"]
    clientes = get_clientes_usuario(usuario_id)

    if not clientes:
        st.info("No tenés clientes asignados.")
        return

    # ── Filtros ──────────────────────────────────────────────
    with st.expander("🔍 Filtros", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            opciones_clientes = ["Todos"] + [c["nombre"] for c in clientes]
            filtro_cliente = st.selectbox("Cliente", opciones_clientes, key="bit_cli")
        with col2:
            filtro_tipo = st.selectbox("Tipo de reunión", [
                "Todos", "Seguimiento operativo mensual", "Reunion puntual",
                "Reclamos", "Comercial", "Interna", "Otra"
            ], key="bit_tipo")
        with col3:
            filtro_calif = st.selectbox("Calificación", [
                "Todas", "positiva", "neutra", "negativa"
            ], key="bit_calif")
        with col4:
            hoy = date.today()
            filtro_desde = st.date_input("Desde", value=hoy - timedelta(days=90), key="bit_desde")
            filtro_hasta = st.date_input("Hasta", value=hoy, key="bit_hasta")

    # ── Construir query ──────────────────────────────────────
    q = sb.table("reuniones")\
        .select("*, clientes(nombre), programas(nombre), usuarios_atento(nombre, apellido)")\
        .gte("fecha", str(filtro_desde))\
        .lte("fecha", str(filtro_hasta))\
        .order("fecha", desc=True)

    # Filtrar por clientes accesibles
    if filtro_cliente == "Todos":
        ids_accesibles = [c["id"] for c in clientes]
        q = q.in_("cliente_id", ids_accesibles)
    else:
        cliente_obj = next((c for c in clientes if c["nombre"] == filtro_cliente), None)
        if cliente_obj:
            q = q.eq("cliente_id", cliente_obj["id"])

    if filtro_tipo != "Todos":
        q = q.eq("tipo_reunion", filtro_tipo)
    if filtro_calif != "Todas":
        q = q.eq("calificacion", filtro_calif)

    reuniones = q.execute().data

    # ── Contador ─────────────────────────────────────────────
    st.markdown(f"**{len(reuniones)} reuniones encontradas**")

    if not reuniones:
        st.info("No se encontraron reuniones con los filtros aplicados.")
        return

    # ── Lista de reuniones ───────────────────────────────────
    for r in reuniones:
        cliente_nombre  = (r.get("clientes") or {}).get("nombre", "—")
        programa_nombre = (r.get("programas") or {}).get("nombre")
        usuario_nombre  = f"{(r.get('usuarios_atento') or {}).get('nombre', '')} {(r.get('usuarios_atento') or {}).get('apellido', '')}".strip()
        calific_html    = CALIFICACION_HTML.get(r.get("calificacion", "neutra"), "")
        programa_txt    = f" · {programa_nombre}" if programa_nombre else ""

        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"""
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <span style="font-size:16px;font-weight:700;">{cliente_nombre}{programa_txt}</span>
                            &nbsp; {calific_html}
                        </div>
                        <div style="font-size:13px;color:#6b7280;">{r.get('fecha', '')}</div>
                    </div>
                    <div style="font-size:13px;color:#4b5563;margin-top:6px;">
                        🗂 {r.get('tipo_reunion', '')} &nbsp;·&nbsp;
                        👤 {usuario_nombre or 'Sin datos'}
                        {f" &nbsp;·&nbsp; 🕐 {r.get('hora', '')}" if r.get('hora') else ""}
                    </div>
                    {f'<div style="font-size:13px;color:#6b7280;margin-top:4px;font-style:italic;">{r.get("observaciones","")[:120]}{"..." if len(r.get("observaciones","") or "") > 120 else ""}</div>' if r.get("observaciones") else ""}
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Ver detalle", key=f"ver_{r['id']}", use_container_width=True):
                    st.session_state["reunion_detalle_id"] = r["id"]
                    st.session_state["reunion_detalle_data"] = r

    # ── Panel de detalle ─────────────────────────────────────
    if st.session_state.get("reunion_detalle_id"):
        _mostrar_detalle(sb, st.session_state["reunion_detalle_id"],
                         st.session_state.get("reunion_detalle_data", {}))


def _mostrar_detalle(sb, reunion_id: str, r: dict):
    st.markdown("---")
    cliente_nombre  = (r.get("clientes") or {}).get("nombre", "—")
    programa_nombre = (r.get("programas") or {}).get("nombre", "")

    st.markdown(f"## 🔍 Detalle: {cliente_nombre}{f' · {programa_nombre}' if programa_nombre else ''}")

    col_cerrar, _ = st.columns([1, 5])
    with col_cerrar:
        if st.button("✖ Cerrar detalle"):
            st.session_state.pop("reunion_detalle_id", None)
            st.session_state.pop("reunion_detalle_data", None)
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Datos", "👥 Asistentes", "📌 Items", "📎 Adjuntos"])

    # ── Tab 1: Datos generales ───────────────────────────────
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fecha", r.get("fecha", "—"))
            st.metric("Hora", r.get("hora", "—") or "—")
        with col2:
            st.metric("Tipo", r.get("tipo_reunion", "—"))
            calif = r.get("calificacion", "neutra")
            st.metric("Calificación", calif.capitalize())
        with col3:
            usuario_nombre = f"{(r.get('usuarios_atento') or {}).get('nombre', '')} {(r.get('usuarios_atento') or {}).get('apellido', '')}".strip()
            st.metric("Registrado por", usuario_nombre or "—")
            st.metric("Fecha registro", str(r.get("fecha_registro", "—"))[:10])

        if r.get("observaciones"):
            st.markdown("**Observaciones:**")
            st.info(r["observaciones"])

    # ── Tab 2: Asistentes ────────────────────────────────────
    with tab2:
        col_cli, col_aten = st.columns(2)

        with col_cli:
            st.markdown("**Asistentes del cliente**")
            asistentes = sb.table("reunion_asistentes_cliente")\
                .select("contactos_cliente(nombre, apellido, cargo, area, email, movil)")\
                .eq("reunion_id", reunion_id).execute().data
            if asistentes:
                for a in asistentes:
                    c = a.get("contactos_cliente", {}) or {}
                    st.markdown(f"""
                    <div class="card" style="padding:10px 14px;">
                        <b>{c.get('nombre','')} {c.get('apellido','')}</b><br>
                        <span style="font-size:12px;color:#6b7280;">{c.get('cargo','—')} · {c.get('area','—')}</span><br>
                        <span style="font-size:12px;">📧 {c.get('email','—')} &nbsp; 📱 {c.get('movil','—')}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Sin asistentes del cliente registrados.")

        with col_aten:
            st.markdown("**Asistentes de Atento**")
            asistentes_a = sb.table("reunion_asistentes_atento")\
                .select("usuarios_atento(nombre, apellido)")\
                .eq("reunion_id", reunion_id).execute().data
            if asistentes_a:
                for a in asistentes_a:
                    u = a.get("usuarios_atento", {}) or {}
                    st.markdown(f"""
                    <div class="card" style="padding:10px 14px;">
                        👤 <b>{u.get('nombre','')} {u.get('apellido','')}</b>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("Sin asistentes de Atento registrados.")

    # ── Tab 3: Items de seguimiento ──────────────────────────
    with tab3:
        items = sb.table("items_seguimiento")\
            .select("*").eq("reunion_id", reunion_id)\
            .order("tipo").execute().data

        if not items:
            st.info("No hay items de seguimiento en esta reunión.")
        else:
            for item in items:
                icono = TIPO_ICONO.get(item["tipo"], "•")
                estado_txt = ESTADO_HTML.get(item["estado"], item["estado"])
                col1, col2, col3, col4 = st.columns([0.5, 3, 1.5, 1.5])
                with col1:
                    st.markdown(f"<div style='font-size:22px;margin-top:8px;'>{icono}</div>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{item['descripcion']}**")
                    if item.get("notas_seguimiento"):
                        st.caption(item["notas_seguimiento"])
                with col3:
                    st.markdown(f"{estado_txt}")
                    if item.get("responsable"):
                        st.caption(f"👤 {item['responsable']}")
                with col4:
                    if item.get("fecha_compromiso"):
                        st.caption(f"📅 {item['fecha_compromiso']}")
                    # Edición rápida de estado
                    nuevo_estado = st.selectbox(
                        "Actualizar",
                        ["pendiente", "en_curso", "resuelto"],
                        index=["pendiente", "en_curso", "resuelto"].index(item["estado"]),
                        key=f"est_{item['id']}",
                        label_visibility="collapsed"
                    )
                    if nuevo_estado != item["estado"]:
                        sb.table("items_seguimiento")\
                            .update({"estado": nuevo_estado,
                                     "fecha_cierre": str(date.today()) if nuevo_estado == "resuelto" else None})\
                            .eq("id", item["id"]).execute()
                        st.rerun()
                st.divider()

    # ── Tab 4: Adjuntos ──────────────────────────────────────
    with tab4:
        adjuntos = sb.table("adjuntos")\
            .select("*").eq("reunion_id", reunion_id).execute().data

        if not adjuntos:
            st.info("No hay adjuntos en esta reunión.")
        else:
            for adj in adjuntos:
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    icono = "🔗" if adj["tipo"] == "link" else "📄"
                    st.markdown(f"{icono} **{adj['nombre']}**")
                with col2:
                    if adj.get("url"):
                        st.link_button("🔗 Abrir", adj["url"])
                with col3:
                    # Botón de descarga para archivos de Supabase Storage
                    if adj["tipo"] == "archivo" and adj.get("storage_path"):
                        try:
                            import requests as req
                            supabase_url = st.secrets["SUPABASE_URL"]
                            anon_key     = st.secrets["SUPABASE_ANON_KEY"]
                            dl_url = f"{supabase_url}/storage/v1/object/adjuntos-reuniones/{adj['storage_path']}"
                            r = req.get(dl_url, headers={"apikey": anon_key}, timeout=15)
                            if r.status_code == 200:
                                st.download_button(
                                    "⬇️ Bajar",
                                    data=r.content,
                                    file_name=adj["nombre"],
                                    mime=r.headers.get("content-type","application/octet-stream"),
                                    key=f"dl_{adj['id']}"
                                )
                        except Exception:
                            pass
