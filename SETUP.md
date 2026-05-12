# 📋 Bitácora Atento — Guía de Setup y Deploy

## Estructura del proyecto

```
bitacora_app/
├── app.py                          ← Punto de entrada principal
├── requirements.txt
├── supabase_schema.sql             ← Schema principal (ejecutar primero)
├── supabase_extras.sql             ← Sesiones + triggers + equipo
├── .streamlit/
│   └── secrets.toml.template      ← Plantilla de secrets
├── pages/
│   ├── dashboard.py               ← Dashboard con alertas
│   ├── nueva_reunion.py           ← Formulario de reunión
│   ├── bitacora.py                ← Listado y detalle
│   ├── pendientes.py              ← Items de seguimiento
│   ├── contactos.py               ← ABM contactos
│   └── admin.py                   ← Administración
└── utils/
    ├── supabase_client.py         ← Conexión + helpers
    └── auth.py                    ← Google OAuth + sesión única
```

---

## PASO 1 — Configurar Supabase

### 1.1 Crear proyecto
- Ir a https://supabase.com → New Project
- Nombre: `bitacora-atento` · Región: South America (São Paulo)
- Guardar la contraseña de la DB

### 1.2 Ejecutar SQL
En el **SQL Editor** de Supabase, ejecutar en orden:
1. `supabase_schema.sql` (schema completo + clientes precargados)
2. `supabase_extras.sql` (sesiones + triggers + equipo)

> ⚠️ En `supabase_extras.sql`, reemplazá `sebas@gmail.com` por tu email real de Google

### 1.3 Crear Storage Bucket
- Dashboard → Storage → New Bucket
- Nombre: `adjuntos-reuniones`
- Public: **NO**
- Max file size: 20MB

### 1.4 Configurar Google OAuth
- Dashboard → Authentication → Providers → Google → Enable
- Crear proyecto en https://console.cloud.google.com
  - APIs & Services → Credentials → OAuth 2.0 Client IDs
  - Application type: Web application
  - Authorized redirect URIs: `https://xxxx.supabase.co/auth/v1/callback`
- Pegar Client ID y Client Secret en Supabase → Auth → Google

### 1.5 Obtener claves API
- Dashboard → Settings → API
- Copiar: `Project URL`, `anon key`, `service_role key`

---

## PASO 2 — Configurar Streamlit Cloud

### 2.1 Subir código a GitHub
```bash
cd bitacora_app
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/bitacora-atento.git
git push -u origin main
```

> Asegurate de tener un `.gitignore` con:
> ```
> .streamlit/secrets.toml
> __pycache__/
> *.pyc
> ```

### 2.2 Deploy en Streamlit Cloud
- Ir a https://share.streamlit.io → New app
- Seleccionar tu repo → branch: `main` → Main file: `app.py`
- Copiar la URL de tu app (ej: `https://bitacora-atento.streamlit.app`)

### 2.3 Configurar secrets
En Streamlit Cloud → App settings → Secrets, pegar:
```toml
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGc..."
SUPABASE_SERVICE_KEY = "eyJhbGc..."
REDIRECT_URL = "https://bitacora-atento.streamlit.app"
```

### 2.4 Actualizar redirect URL en Google Cloud Console
- Agregar a "Authorized redirect URIs":
  `https://bitacora-atento.streamlit.app` (la URL real de tu app)

---

## PASO 3 — Primer login

1. Abrir la app → clic en "Ingresar con Google"
2. Loguear con tu cuenta Google (la que pusiste en `supabase_extras.sql`)
3. El sistema te va a reconocer como admin y dejar entrar directamente
4. Si alguien más se loguea por primera vez, va a quedar pendiente y vos lo activás desde Admin → Usuarios

---

## Flujo de gestión de usuarios

```
Usuario nuevo → Login Google → Estado: PENDIENTE (inactivo)
       ↓
Admin → Panel Admin → Usuarios → Activar + asignar rol + clientes
       ↓
Usuario puede ingresar con acceso solo a sus clientes asignados
```

---

## Funcionalidades incluidas

| Módulo | Funcionalidades |
|--------|----------------|
| **Dashboard** | Alertas clientes sin reunión del mes, últimas reuniones, items pendientes, métricas |
| **Nueva Reunión** | Formulario completo con cliente/programa, asistentes, adjuntos, items de seguimiento |
| **Bitácora** | Filtros por cliente/tipo/calificación/fecha, detalle con tabs, edición de estado de items |
| **Pendientes** | Vista consolidada de pedidos/reclamos/reconocimientos, actualización rápida de estado, notas |
| **Contactos** | ABM completo con datos profesionales + personales, alerta de cumpleaños próximo |
| **Admin** | Activación de usuarios, roles, permisos por cliente, gestión de clientes y programas |

---

## Próximos módulos sugeridos (fase 2)

- 📊 **IRS / Margen de Contribución** — integración financiera por cuenta
- 📧 **Recordatorios por email** — via Supabase Edge Functions + Resend
- 🤖 **Asistente IA** — análisis de reuniones, sugerencias de acción (Anthropic API)
- 📤 **Exportación** — reportes PDF/Excel por cliente y período
- 📱 **Notificaciones push** — alertas de vencimiento de items

---

## Soporte y contacto
Desarrollado para Atento · Delivery Management · Argentina & Uruguay
```
