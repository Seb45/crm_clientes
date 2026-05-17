"""
utils/notificaciones.py
Notificaciones via Telegram — detalle completo
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
import streamlit as st
from datetime import datetime
import pytz


def _hora_ar() -> str:
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%d/%m/%Y %H:%M")


def _enviar(mensaje: str):
    try:
        token   = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"},
            timeout=5
        )
    except Exception:
        pass


# ── LOGIN ────────────────────────────────────────────────────

def notif_login(usuario: dict):
    _enviar(
        f"🔐 <b>LOGIN — Bitácora Atento</b>\n"
        f"{'─'*30}\n"
        f"👤 <b>{usuario['nombre']} {usuario.get('apellido','')}</b>\n"
        f"📧 {usuario['email']}\n"
        f"🎖 Rol: {usuario['rol'].upper()}\n"
        f"🕐 {_hora_ar()}"
    )


# ── LOGOUT ───────────────────────────────────────────────────

def notif_logout(usuario: dict):
    _enviar(
        f"🚪 <b>LOGOUT</b>\n"
        f"{'─'*30}\n"
        f"👤 {usuario['nombre']} {usuario.get('apellido','')}\n"
        f"📧 {usuario['email']}\n"
        f"🕐 {_hora_ar()}"
    )


# ── NUEVA REUNIÓN ────────────────────────────────────────────

def notif_nueva_reunion(
    usuario: dict,
    cliente: str,
    tipo: str,
    fecha: str,
    hora: str = None,
    programa: str = None,
    calificacion: str = None,
    observaciones: str = None,
    asistentes_cliente: list = None,
    asistentes_atento: list = None,
    items: list = None,
    adjuntos: list = None,
):
    cal_icon = {"positiva": "✅", "neutra": "➖", "negativa": "❌"}.get(calificacion, "➖")
    prog_txt = f" · <i>{programa}</i>" if programa else ""
    hora_txt = f" {hora}" if hora else ""

    lineas = [
        f"📋 <b>NUEVA REUNIÓN</b>",
        f"{'─'*30}",
        f"🏢 <b>{cliente}</b>{prog_txt}",
        f"📅 {fecha}{hora_txt}",
        f"🗂 {tipo}",
        f"{cal_icon} Calificación: <b>{(calificacion or 'neutra').capitalize()}</b>",
        f"👤 Cargada por: {usuario['nombre']} {usuario.get('apellido','')}",
    ]

    # Asistentes cliente
    if asistentes_cliente:
        nombres = [f"{c.get('nombre','')} {c.get('apellido','')} ({c.get('cargo','') or '—'})" for c in asistentes_cliente]
        lineas.append(f"\n👥 <b>Asistentes cliente:</b>")
        for n in nombres:
            lineas.append(f"  • {n.strip()}")

    # Asistentes Atento
    if asistentes_atento:
        lineas.append(f"\n🏷 <b>Asistentes Atento:</b>")
        for u in asistentes_atento:
            lineas.append(f"  • {u.get('nombre','')} {u.get('apellido','')}")

    # Observaciones
    if observaciones and observaciones.strip():
        lineas.append(f"\n📝 <b>Observaciones:</b>")
        lineas.append(f"  {observaciones[:300]}{'...' if len(observaciones)>300 else ''}")

    # Items de seguimiento
    if items:
        tipo_icon = {"pedido": "📌", "reclamo": "⚠️", "reconocimiento": "🏆"}
        estado_txt = {"pendiente": "🔴", "en_curso": "🟡", "resuelto": "🟢"}
        lineas.append(f"\n📋 <b>Items de seguimiento ({len(items)}):</b>")
        for item in items:
            if item.get("descripcion"):
                ic  = tipo_icon.get(item.get("tipo",""), "•")
                est = estado_txt.get(item.get("estado",""), "•")
                resp = f" → {item['responsable']}" if item.get("responsable") else ""
                fc   = f" 📅{item['fecha_compromiso']}" if item.get("fecha_compromiso") else ""
                lineas.append(f"  {ic} {est} {item['descripcion'][:60]}{resp}{fc}")

    # Adjuntos
    if adjuntos:
        lineas.append(f"\n📎 <b>Adjuntos ({len(adjuntos)}):</b>")
        for adj in adjuntos:
            ic = "🔗" if adj.get("tipo") == "link" else "📄"
            lineas.append(f"  {ic} {adj.get('nombre','')[:50]}")

    lineas.append(f"\n🕐 {_hora_ar()}")
    _enviar("\n".join(lineas))


# ── NUEVO CONTACTO ───────────────────────────────────────────

def notif_nuevo_contacto(usuario: dict, contacto: dict, cliente: str):
    nombre_completo = f"{contacto.get('nombre','')} {contacto.get('apellido','')}".strip()

    lineas = [
        f"👥 <b>NUEVO CONTACTO</b>",
        f"{'─'*30}",
        f"🏢 Cliente: <b>{cliente}</b>",
        f"👤 <b>{nombre_completo}</b>",
    ]
    if contacto.get("cargo"):
        lineas.append(f"💼 Cargo: {contacto['cargo']}")
    if contacto.get("area"):
        lineas.append(f"📂 Área: {contacto['area']}")
    if contacto.get("email"):
        lineas.append(f"📧 Email: {contacto['email']}")
    if contacto.get("movil"):
        lineas.append(f"📱 Móvil: {contacto['movil']}")
    if contacto.get("fecha_nacimiento"):
        lineas.append(f"🎂 Nac: {contacto['fecha_nacimiento']}")
    if contacto.get("localidad"):
        lineas.append(f"📍 Localidad: {contacto['localidad']}")

    # Datos personales
    personales = []
    if contacto.get("musica"):     personales.append(f"🎵 {contacto['musica']}")
    if contacto.get("comida"):     personales.append(f"🍽 {contacto['comida']}")
    if contacto.get("deportes"):   personales.append(f"⚽ {contacto['deportes']}")
    if contacto.get("hobbies"):    personales.append(f"🎯 {contacto['hobbies']}")
    if contacto.get("intereses"):  personales.append(f"💡 {contacto['intereses']}")
    if personales:
        lineas.append(f"\n🧩 <b>Datos personales:</b>")
        for p in personales:
            lineas.append(f"  • {p}")

    if contacto.get("notas_personales"):
        lineas.append(f"\n📝 Notas: {contacto['notas_personales'][:200]}")

    lineas.append(f"\n➕ Creado por: {usuario['nombre']} {usuario.get('apellido','')}")
    lineas.append(f"🕐 {_hora_ar()}")
    _enviar("\n".join(lineas))


# ── ITEM ACTUALIZADO ─────────────────────────────────────────

def notif_item_actualizado(usuario: dict, item: dict, cliente: str):
    tipo_icon  = {"pedido": "📌", "reclamo": "⚠️", "reconocimiento": "🏆"}
    estado_txt = {"pendiente": "🔴 Pendiente", "en_curso": "🟡 En curso", "resuelto": "🟢 Resuelto"}

    lineas = [
        f"{tipo_icon.get(item.get('tipo',''), '•')} <b>ITEM ACTUALIZADO</b>",
        f"{'─'*30}",
        f"🏢 Cliente: <b>{cliente}</b>",
        f"📝 {item.get('descripcion','')[:100]}",
        f"Tipo: {(item.get('tipo') or '').capitalize()}",
        f"Estado: {estado_txt.get(item.get('estado',''), item.get('estado',''))}",
    ]
    if item.get("responsable"):
        lineas.append(f"👤 Responsable: {item['responsable']}")
    if item.get("fecha_compromiso"):
        lineas.append(f"📅 Fecha compromiso: {item['fecha_compromiso']}")
    if item.get("fecha_cierre"):
        lineas.append(f"✅ Fecha cierre: {item['fecha_cierre']}")
    if item.get("notas_seguimiento"):
        lineas.append(f"\n💬 <b>Notas:</b>")
        lineas.append(f"  {item['notas_seguimiento'][-300:]}")  # últimas notas

    lineas.append(f"\n👤 Actualizado por: {usuario['nombre']} {usuario.get('apellido','')}")
    lineas.append(f"🕐 {_hora_ar()}")
    _enviar("\n".join(lineas))


# ── CAMBIO DE CONTRASEÑA ─────────────────────────────────────

def notif_cambio_password(usuario: dict, target_nombre: str = None):
    if target_nombre:
        _enviar(
            f"🔑 <b>CONTRASEÑA RESETEADA</b>\n"
            f"{'─'*30}\n"
            f"🔧 Admin: {usuario['nombre']} {usuario.get('apellido','')}\n"
            f"👤 Usuario afectado: <b>{target_nombre}</b>\n"
            f"🕐 {_hora_ar()}"
        )
    else:
        _enviar(
            f"🔑 <b>CAMBIO DE CONTRASEÑA</b>\n"
            f"{'─'*30}\n"
            f"👤 {usuario['nombre']} {usuario.get('apellido','')}\n"
            f"📧 {usuario.get('email','')}\n"
            f"🕐 {_hora_ar()}"
        )


# ── USUARIO ACTIVADO ─────────────────────────────────────────

def notif_usuario_activado(admin: dict, nuevo_usuario: str, email: str):
    _enviar(
        f"✅ <b>USUARIO ACTIVADO</b>\n"
        f"{'─'*30}\n"
        f"👤 <b>{nuevo_usuario}</b>\n"
        f"📧 {email}\n"
        f"🔧 Activado por: {admin['nombre']} {admin.get('apellido','')}\n"
        f"🕐 {_hora_ar()}"
    )
