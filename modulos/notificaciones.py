"""
utils/notificaciones.py
Notificaciones via Telegram para eventos de la app
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
import streamlit as st
from datetime import datetime
import pytz

def _get_hora_ar() -> str:
    """Retorna la hora actual en Argentina."""
    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    return datetime.now(tz).strftime("%d/%m/%Y %H:%M")


def _enviar(mensaje: str):
    """Envía un mensaje al canal de Telegram."""
    try:
        token   = st.secrets["TELEGRAM_BOT_TOKEN"]
        chat_id = st.secrets["TELEGRAM_CHAT_ID"]
        url     = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={
            "chat_id":    chat_id,
            "text":       mensaje,
            "parse_mode": "HTML",
        }, timeout=5)
    except Exception:
        pass  # Nunca romper la app por falla de notificación


# ── Eventos ──────────────────────────────────────────────────

def notif_login(usuario: dict):
    _enviar(
        f"🔐 <b>Login</b>\n"
        f"👤 {usuario['nombre']} {usuario.get('apellido','')} ({usuario['rol']})\n"
        f"📧 {usuario['email']}\n"
        f"🕐 {_get_hora_ar()}"
    )


def notif_nueva_reunion(usuario: dict, cliente: str, tipo: str, fecha: str, programa: str = None):
    prog = f" · {programa}" if programa else ""
    _enviar(
        f"📋 <b>Nueva Reunión</b>\n"
        f"🏢 {cliente}{prog}\n"
        f"📅 {fecha} · {tipo}\n"
        f"👤 Cargada por {usuario['nombre']} {usuario.get('apellido','')}\n"
        f"🕐 {_get_hora_ar()}"
    )


def notif_nuevo_contacto(usuario: dict, nombre: str, cliente: str):
    _enviar(
        f"👥 <b>Nuevo Contacto</b>\n"
        f"👤 {nombre} — {cliente}\n"
        f"➕ Creado por {usuario['nombre']} {usuario.get('apellido','')}\n"
        f"🕐 {_get_hora_ar()}"
    )


def notif_item_actualizado(usuario: dict, tipo: str, descripcion: str, estado: str, cliente: str):
    iconos = {"pedido": "📌", "reclamo": "⚠️", "reconocimiento": "🏆"}
    estados = {"pendiente": "🔴 Pendiente", "en_curso": "🟡 En curso", "resuelto": "🟢 Resuelto"}
    _enviar(
        f"{iconos.get(tipo,'•')} <b>Item actualizado</b>\n"
        f"🏢 {cliente}\n"
        f"📝 {descripcion[:80]}\n"
        f"Estado: {estados.get(estado, estado)}\n"
        f"👤 {usuario['nombre']} {usuario.get('apellido','')}\n"
        f"🕐 {_get_hora_ar()}"
    )


def notif_cambio_password(usuario: dict, target_nombre: str = None):
    if target_nombre:
        _enviar(
            f"🔑 <b>Contraseña reseteada</b>\n"
            f"👤 Admin: {usuario['nombre']} {usuario.get('apellido','')}\n"
            f"🔧 Usuario afectado: {target_nombre}\n"
            f"🕐 {_get_hora_ar()}"
        )
    else:
        _enviar(
            f"🔑 <b>Cambio de contraseña</b>\n"
            f"👤 {usuario['nombre']} {usuario.get('apellido','')}\n"
            f"🕐 {_get_hora_ar()}"
        )


def notif_usuario_activado(admin: dict, nuevo_usuario: str, email: str):
    _enviar(
        f"✅ <b>Usuario activado</b>\n"
        f"👤 {nuevo_usuario} ({email})\n"
        f"🔧 Por: {admin['nombre']} {admin.get('apellido','')}\n"
        f"🕐 {_get_hora_ar()}"
    )


def notif_logout(usuario: dict):
    _enviar(
        f"🚪 <b>Logout</b>\n"
        f"👤 {usuario['nombre']} {usuario.get('apellido','')}\n"
        f"🕐 {_get_hora_ar()}"
    )
