"""
pages/dashboard.py
Dashboard principal: alertas + últimas reuniones + pendientes
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.supabase_client import (
    get_supabase,
    get_clientes_sin_reunion_mes,
    get_ultimas_reuniones,
    get_items_pendientes,
)

CALIFICACION_HTML = {
    "positiva": '<span class="chip-positiva">✅ Positiva</span>',
    "neutra":   '<span class="chip-neutra">➖ Neutra</span>',
    "negativa": '<span class="chip-negativa">❌ Negativa</span>',
}

ESTADO_HTML = {
    "pendiente": '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">Pendiente</span>',
    "en_curso":  '<span style="background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">En curso</span>',
    "resuelto":  '<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;">Resuelto</span>',
}

TIPO_ICONO = {
    "pedido": "📌",
    "reclamo": "⚠️",
    "reconocimiento": "🏆",
}


def show(usuario: dict):
    st.markdown(f"## 🏠 Dashboard")
    st.markdown(f"Bienvenido, **{usuario['nombre']}** — {date.today().strftime('%A %d de %B de %Y')}")
    st.divider()

    usuario_id = usuario["id"]

    # ── Métricas rápidas ─────────────────────────────────────
    clientes_sin_reunion = get_clientes_sin_reunion_mes(usuario_id)
    ultimas_reuniones    = get_ultimas_reuniones(usuario_id, limit=50)
    items_pendientes     = get_items_pendientes(usuario_id)

    reuniones_mes = _get_reuniones_mes(usuario_id)
    items_vencidos = _get_items_vencidos(items_pendientes)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_box("🚨", str(len(clientes_sin_reunion)), "Clientes sin reunión este mes",
                    color="#fee2e2" if clientes_sin_reunion else "#dcfce7")
    with col2:
        _metric_box("📅", str(len(reuniones_mes)), "Reuniones este mes", color="#e8f0fe")
    with col3:
        _metric_box("📌", str(len(items_pendientes)), "Items pendientes / en curso",
                    color="#fef9c3" if items_pendientes else "#dcfce7")
    with col4:
        _metric_box("⏰", str(len(items_vencidos)), "Items vencidos (sin fecha cierre)",
                    color="#fee2e2" if items_vencidos else "#dcfce7")

    st.markdown("---")

    # ── Dos columnas: alertas + últimas reuniones ────────────
    col_izq, col_der = st.columns([1, 1.6], gap="large")

    with col_izq:
        st.markdown("### 🚨 Clientes sin reunión en el mes")
        if not clientes_sin_reunion:
            st.success("✅ Todos los clientes tienen reunión registrada este mes.")
        else:
            for c in clientes_sin_reunion:
                st.markdown(f"""
                <div class="card card-alerta">
                    <b>{c['nombre']}</b>
                    <div style="font-size:12px;color:#6b7280;margin-top:4px;">Sin reunión en {date.today().strftime('%B %Y')}</div>
                </div>
                """, unsafe_allow_html=True)

        # Items pendientes vencidos
        if items_vencidos:
            st.markdown("### ⏰ Items vencidos")
            for item in items_vencidos[:5]:
                cliente_nombre = _safe_nested(item, "reuniones", "clientes", "nombre")
                st.markdown(f"""
                <div class="card card-alerta">
                    {TIPO_ICONO.get(item['tipo'], '•')} <b>{item['descripcion'][:60]}</b>
                    <div style="font-size:12px;color:#6b7280;margin-top:4px;">{cliente_nombre} · Responsable: {item.get('responsable') or 'Sin asignar'}</div>
                </div>
                """, unsafe_allow_html=True)

    with col_der:
        st.markdown("### 📋 Últimas reuniones registradas")
        if not ultimas_reuniones:
            st.info("No hay reuniones registradas aún.")
        else:
            for r in ultimas_reuniones[:8]:
                cliente_nombre = _safe_nested(r, "clientes", "nombre") or "—"
                programa_nombre = _safe_nested(r, "programas", "nombre")
                usuario_nombre  = _safe_nested(r, "usuarios_atento", "nombre") or ""
                calific_html    = CALIFICACION_HTML.get(r.get("calificacion", "neutra"), "")
                fecha_str       = r.get("fecha", "")
                tipo            = r.get("tipo_reunion", "")

                st.markdown(f"""
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <b style="font-size:15px;">{cliente_nombre}</b>
                            {f'<span style="font-size:12px;color:#6b7280;"> · {programa_nombre}</span>' if programa_nombre else ''}
                        </div>
                        {calific_html}
                    </div>
                    <div style="font-size:12px;color:#6b7280;margin-top:6px;">
                        📅 {fecha_str} &nbsp;·&nbsp; {tipo} &nbsp;·&nbsp; 👤 {usuario_nombre}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── Items pendientes recientes ───────────────────────────
    if items_pendientes:
        st.markdown("---")
        st.markdown("### 📌 Items de seguimiento pendientes")

        df_items = []
        for item in items_pendientes:
            cliente_nombre = _safe_nested(item, "reuniones", "clientes", "nombre") or "—"
            reunion_fecha  = _safe_nested(item, "reuniones", "fecha") or "—"
            df_items.append({
                "Tipo": f"{TIPO_ICONO.get(item['tipo'], '')} {item['tipo'].capitalize()}",
                "Descripción": item["descripcion"][:80],
                "Estado": item["estado"].replace("_", " ").capitalize(),
                "Responsable": item.get("responsable") or "—",
                "Cliente": cliente_nombre,
                "Reunión": reunion_fecha,
            })

        df = pd.DataFrame(df_items)
        st.dataframe(df, use_container_width=True, hide_index=True,
                     column_config={"Descripción": st.column_config.TextColumn(width="large")})


# ── Helpers internos ─────────────────────────────────────────

def _metric_box(icon, value, label, color="#e8f0fe"):
    st.markdown(f"""
    <div style="background:{color};border-radius:12px;padding:16px;text-align:center;border:1px solid #e5e7eb;">
        <div style="font-size:28px;">{icon}</div>
        <div style="font-size:30px;font-weight:700;color:#1a3c5e;">{value}</div>
        <div style="font-size:12px;color:#6b7280;margin-top:4px;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def _safe_nested(obj, *keys):
    """Navega dicts anidados retornando None si falla."""
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def _get_reuniones_mes(usuario_id: str) -> list:
    from utils.supabase_client import get_supabase, get_usuario_actual
    sb = get_supabase()
    hoy = date.today()
    primer_dia = hoy.replace(day=1).isoformat()
    usuario = get_usuario_actual()

    if usuario and usuario.get("rol") == "admin":
        return sb.table("reuniones").select("id").gte("fecha", primer_dia).execute().data
    else:
        from utils.supabase_client import get_clientes_usuario
        clientes = get_clientes_usuario(usuario_id)
        ids = [c["id"] for c in clientes]
        if not ids:
            return []
        return sb.table("reuniones").select("id")\
            .gte("fecha", primer_dia).in_("cliente_id", ids).execute().data


def _get_items_vencidos(items: list) -> list:
    """Items pendientes/en_curso sin fecha de compromiso o con fecha pasada."""
    hoy = date.today()
    vencidos = []
    for item in items:
        fc = item.get("fecha_compromiso")
        if fc:
            try:
                if date.fromisoformat(fc) < hoy:
                    vencidos.append(item)
            except Exception:
                pass
        # Sin fecha de compromiso con más de 30 días de antigüedad
        elif item.get("created_at"):
            try:
                from datetime import datetime
                created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                if (datetime.now(created.tzinfo) - created).days > 30:
                    vencidos.append(item)
            except Exception:
                pass
    return vencidos
