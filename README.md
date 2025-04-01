# 🤖 Bot de Telegram para Coes Sneakers

Bot oficial para la gestión de productos, precios y tallas en los grupos de Coes Sneakers. Incluye integración con Flask para despliegue en Render.

## ✨ Funcionalidades principales
- Registro de productos (modelo, tallas, precio) mediante fotos + descripción
- Comandos rápidos (`/price`, `/size`, `/buscar`)
- Mensajes de bienvenida/despedida automáticos
- Persistencia de datos en JSON
- **Nuevo**: Servidor web integrado (Flask) para compatibilidad con Render

## 🛠️ Tecnologías utilizadas
- Python 3.10+
- [python-telegram-bot](https://python-telegram-bot.org/) (v20.6)
- Flask (v3.0.0)
- Render (para despliegue)

## 📦 Estructura del proyecto
├── chokolo_bot.py # Script principal del bot
├── requirements.txt # Dependencias (optimizadas)
├── .env # Variables de entorno (ejemplo)
├── carpeta/ # Datos persistentes
│ ├── nombre.json # Base de datos de productos
│ └── backups/ # Copias de seguridad
└── README.md # Este archivo

## 🚀 Despliegue en Render
1. **Conectar repositorio** de GitHub a Render
2. **Configurar variables de entorno**:
   - `TELEGRAM_BOT_TOKEN`: Tu token de BotFather
   - `PORT`: 10000 (Render lo inyecta automáticamente)
3. **Especificar comandos**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python chokolo_bot.py`

## 🔄 Actualizaciones recientes
### v1.1 - Integración con Flask
- ✅ Añadido servidor web Flask (escucha en `0.0.0.0:$PORT`)
- ✅ Nuevo endpoint `/` para verificación de estado
- ✅ Compatibilidad con pings de Render
- ✅ Optimización de dependencias (`requirements.txt`)

## 📌 Comandos disponibles
| Comando       | Descripción                          | Ejemplo               |
|---------------|--------------------------------------|-----------------------|
| `/price`      | Muestra lista de precios            | `/price`              |
| `/size`       | Muestra guía de tallas              | `/size`               |
| `/buscar`     | Busca productos                     | `/buscar Air Force 1` |
| `/eliminar`   | Elimina un producto (admin)         | `/eliminar Nike 10.5` |

## 🌐 Endpoints web
- `GET /` → Verifica estado del bot (`{"status": "ok"}`)
- `POST /webhook` → (Reservado para futuras integraciones)

---

> **Nota**: Los administradores pueden registrar productos enviando una foto + descripción con formato:  
> `Modelo\nTalla X - $Precio`