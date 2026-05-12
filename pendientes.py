"""
pages/pendientes.py
Vista consolidada de todos los items de seguimiento pendientes/en curso
"""

import streamlit as st
import pandas as pd
from datetime import date
from utils.supabase_client import get_supabase, get_items_pendientes, get_clientes_usuario

TIPO_ICONO = {"pedido": "📌", "reclamo": "⚠️", "reconocimiento": "🏆"}
ESTADO_COLOR = {
    "pendiente": "#fee2e2",
    "en_curso":  "#fef9c3",
    "resuelto":  "#dcfce7",
}
ESTADO_TEXT = {
    "pendiente": "🔴 Pendiente",
    "en_curso":  "🟡 En curso",
    "resuelto":  "🟢 Resuelto",
}


def show(usuario: dict):
    st.markdown("## ✅ Items de Seguimiento")
    st.divider()

    sb = get_supabase()
    usuario_id = usuario["id"]

    # ── Filtros ──────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtro_tipo = st.selectbox("Tipo", ["Todos", "pedido", "reclamo", "reconocimiento"],
                                   format_func=lambda t: f"{TIPO_ICONO.get(t, '')} {t.capitalize()}" if t != "Todos" else "Todos")
    with col2:
        filtro_estado = st.selectbox("Estado", ["pendiente", "en_curso", "Todos (incl. resueltos)"],
                                     format_func=lambda e: ESTADO_TEXT.get(e, e))
    with col3:
        clientes = get_clientes_usuario(usuario_id)
        opciones_clientes = ["Todos"] + [c["nombre"] for c in clientes]
        filtro_cliente = st.selectbox("Cliente", opciones_clientes)
    with col4:
        filtro_resp = st.text_input("Responsable (buscar)", placeholder="Nombre...")

    # ── Cargar items ─────────────────────────────────────────
    # Base: pendientes y en_curso
    if filtro_estado == "Todos (incl. resueltos)":
        estados_filtrar = ["pendiente", "en_curso", "resuelto"]
    else:
        estados_filtrar = [filtro_estado]

    if usuario["rol"] == "admin":
        q = sb.table("items_seguimiento")\
            .select("*, reuniones(id, fecha, cliente_id, clientes(nombre))")\
            .in_("estado", estados_filtrar)\
            .order("created_at", desc=True)
    else:
        accesos = sb.table("accesos_usuarios")\
            .select("cliente_id").eq("usuario_id", usuario_id).execute().data
        ids_cli = [a["cliente_id"] for a in accesos]
        if not ids_cli:
            st.info("No tenés clientes asignados.")
            return
        reuniones_ids = [r["id"] for r in
                         sb.table("reuniones").select("id").in_("cliente_id", ids_cli).execute().data]
        if not reuniones_ids:
            st.info("No hay reuniones registradas.")
            return
        q = sb.table("items_seguimiento")\
            .select("*, reuniones(id, fecha, cliente_id, clientes(nombre))")\
            .in_("reunion_id", reuniones_ids)\
            .in_("estado", estados_filtrar)\
            .order("created_at", desc=True)

    items = q.execute().data

    # Filtros adicionales en Python
    if filtro_tipo != "Todos":
        items = [i for i in items if i["tipo"] == filtro_tipo]
    if filtro_cliente != "Todos":
        items = [i for i in items if
                 (i.get("reuniones") or {}).get("clientes", {}).get("nombre") == filtro_cliente]
    if filtro_resp:
        items = [i for i in items if filtro_resp.lower() in (i.get("responsable") or "").lower()]

    # ── Métricas ─────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    total_pend = sum(1 for i in items if i["estado"] == "pendiente")
    total_curso = sum(1 for i in items if i["estado"] == "en_curso")
    total_res = sum(1 for i in items if i["estado"] == "resuelto")
    total_venc = sum(1 for i in items if _esta_vencido(i))

    with c1: _mini_metric("🔴", total_pend, "Pendientes")
    with c2: _mini_metric("🟡", total_curso, "En curso")
    with c3: _mini_metric("🟢", total_res, "Resueltos")
    with c4: _mini_metric("⏰", total_venc, "Vencidos")

    st.markdown("---")

    if not items:
        st.success("✅ No hay items con los filtros seleccionados.")
        return

    # ── Tabla de items ───────────────────────────────────────
    st.markdown(f"**{len(items)} items encontrados**")

    # Agrupar por tipo para mejor lectura
    for tipo in ["reclamo", "pedido", "reconocimiento"]:
        items_tipo = [i for i in items if i["tipo"] == tipo]
        if not items_tipo:
            continue

        icono = TIPO_ICONO[tipo]
        st.markdown(f"### {icono} {tipo.capitalize()}s ({len(items_tipo)})")

        for item in items_tipo:
            cliente_nombre = ((item.get("reuniones") or {}).get("clientes") or {}).get("nombre", "—")
            reunion_fecha  = (item.get("reuniones") or {}).get("fecha", "—")
            estado = item.get("estado", "pendiente")
            bg_color = ESTADO_COLOR.get(estado, "#f9fafb")
            vencido = _esta_vencido(item)

            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3.5, 1.5, 1.5, 1.5, 1])

                with col1:
                    alerta = " ⏰" if vencido else ""
                    st.markdown(f"**{item['descripcion']}{alerta}**")
                    st.caption(f"📅 Reunión: {reunion_fecha} · 🏢 {cliente_nombre}")
                    if item.get("notas_seguimiento"):
                        st.caption(f"💬 {item['notas_seguimiento']}")

                with col2:
                    st.markdown(f"""
                    <div style="background:{bg_color};padding:6px 10px;border-radius:8px;font-size:12px;font-weight:600;margin-top:4px;">
                        {ESTADO_TEXT.get(estado, estado)}
                    </div>""", unsafe_allow_html=True)

                with col3:
                    if item.get("responsable"):
                        st.markdown(f"👤 {item['responsable']}")
                    else:
                        st.caption("Sin responsable")

                with col4:
                    if item.get("fecha_compromiso"):
                        fc = item["fecha_compromiso"]
                        color_fc = "#dc2626" if vencido else "#16a34a"
                        st.markdown(f"<span style='color:{color_fc};font-size:13px;font-weight:600;'>📅 {fc}</span>",
                                    unsafe_allow_html=True)
                    else:
                        st.caption("Sin fecha")

                with col5:
                    # Actualizar estado rápido
                    nuevo_estado = st.selectbox(
                        "Estado",
                        ["pendiente", "en_curso", "resuelto"],
                        index=["pendiente", "en_curso", "resuelto"].index(estado),
                        key=f"pend_est_{item['id']}",
                        label_visibility="collapsed"
                    )
                    if nuevo_estado != estado:
                        _actualizar_estado(sb, item["id"], nuevo_estado)

                # Notas rápidas
                with st.expander("✏️ Agregar nota / actualizar responsable", expanded=False):
                    col_n1, col_n2, col_n3 = st.columns([2, 2, 1])
                    with col_n1:
                        nueva_nota = st.text_input("Nota", key=f"nota_{item['id']}", label_visibility="collapsed",
                                                   placeholder="Agregar nota de seguimiento...")
                    with col_n2:
                        nuevo_resp = st.text_input("Responsable", value=item.get("responsable") or "",
                                                   key=f"resp_{item['id']}", label_visibility="collapsed",
                                                   placeholder="Responsable...")
                    with col_n3:
                        if st.button("Guardar", key=f"save_{item['id']}"):
                            update = {}
                            if nueva_nota:
                                notas_prev = item.get("notas_seguimiento") or ""
                                update["notas_seguimiento"] = f"{notas_prev}\n[{date.today()}] {nueva_nota}".strip()
                            if nuevo_resp:
                                update["responsable"] = nuevo_resp
                            if update:
                                sb.table("items_seguimiento").update(update).eq("id", item["id"]).execute()
                                st.rerun()

                st.divider()


def _actualizar_estado(sb, item_id: str, nuevo_estado: str):
    update = {"estado": nuevo_estado}
    if nuevo_estado == "resuelto":
        update["fecha_cierre"] = str(date.today())
    sb.table("items_seguimiento").update(update).eq("id", item_id).execute()
    st.rerun()


def _esta_vencido(item: dict) -> bool:
    fc = item.get("fecha_compromiso")
    if not fc:
        return False
    try:
        return date.fromisoformat(fc) < date.today() and item.get("estado") != "resuelto"
    except Exception:
        return False


def _mini_metric(icon, value, label):
    st.markdown(f"""
    <div style="background:#f9fafb;border-radius:10px;padding:12px;text-align:center;border:1px solid #e5e7eb;">
        <div style="font-size:20px;">{icon} <b style="font-size:22px;">{value}</b></div>
        <div style="font-size:12px;color:#6b7280;">{label}</div>
    </div>
    """, unsafe_allow_html=True)
