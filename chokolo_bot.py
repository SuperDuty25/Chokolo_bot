import logging
import re
import json
import os
import shutil
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)
from dotenv import load_dotenv
from flask import Flask, request, jsonify  # Nuevas importaciones

# =============================================
# CONFIGURACIÓN DE FLASK
# =============================================
flask_app = Flask(__name__)  # Cambiado de 'app' a 'flask_app'

@flask_app.route('/')
def home():
    return jsonify({"status": "ok", "message": "Coes Sneakers Bot is running"})

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    return jsonify({"status": "ok"})

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port)

# =============================================
# CONFIGURACIÓN BÁSICA DEL BOT
# =============================================
# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SITIO_WEB = "https://coesneakers.com/"

# Configuración robusta de rutas (evita OneDrive)
BASE_DIR = os.path.expanduser("~")  # Carpeta de usuario
DATA_DIR = os.path.join(BASE_DIR, "coes_bot_data")  # Nueva ubicación
DB_FILE = os.path.join(DATA_DIR, "productos_db.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# Crear carpetas con permisos adecuados
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
except Exception as e:
    logger.error(f"Error al crear directorios: {e}")
    raise

GRUPOS_AUTORIZADOS = [
    -1002592175038,  # Club oficial Coes Sneakers
    -1002586303587,  # Segundo grupo
    -0000000000000   # Tercer grupo (reemplazar con ID real)
]

# Verificación de configuración
if not TOKEN:
    logger.error("No se encontró el TOKEN del bot en las variables de entorno")
    raise ValueError("Token del bot no configurado")

logger.info(f"Directorio de datos: {DATA_DIR}")
logger.info(f"Archivo de base de datos: {DB_FILE}")

# =============================================
# SISTEMA DE PERSISTENCIA JSON MEJORADO
# =============================================
def cargar_db():
    """Carga la base de datos con manejo robusto de errores"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error cargando DB: {e}")
        return {}

def guardar_db():
    """Guarda la base de datos con verificación de permisos"""
    try:
        temp_file = DB_FILE + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(productos_db, f, ensure_ascii=False, indent=2)
        
        # Reemplazo atómico para evitar corrupción
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        os.rename(temp_file, DB_FILE)
        
    except Exception as e:
        logger.error(f"Error guardando DB: {e}")

def hacer_backup():
    """Crea backups con verificación de archivos"""
    try:
        if os.path.exists(DB_FILE):
            fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{fecha}.json")
            
            # Método más seguro para copiar
            with open(DB_FILE, 'r', encoding='utf-8') as orig, \
                 open(backup_file, 'w', encoding='utf-8') as backup:
                backup.write(orig.read())
                
    except Exception as e:
        logger.error(f"Error en backup: {e}")

# Cargar la base de datos al iniciar
productos_db = cargar_db()
logger.info(f"Base de datos cargada. Productos registrados: {len(productos_db)}")

# Patrón más flexible para productos
PATRON_PRODUCTO = re.compile(
    r'^(?P<modelo>.+?)\n'  # Nombre del modelo (hasta el salto de línea)
    r'(?:Talla|Tallas)?[:\s]*'  # Opcional: "Talla"/"Tallas" con posibles ":" o espacios
    r'(?P<tallas>[\d\.]+(?:\s*(?:,|y|\/)\s*[\d\.]+)*)\s*'  # Tallas (pueden ser múltiples)
    r'[-–—]\s*'  # Separador (guión normal, guión largo o em dash)
    r'(?P<precio>(?:\$|USD\s*)?\d+(?:\s*USD|\s*\$\s*)?)',  # Precio en cualquier formato
    re.IGNORECASE | re.MULTILINE
)

# =============================================
# MENSAJES PREDEFINIDOS (TEXTO ORIGINAL)
# =============================================
MENSAJE_BIENVENIDA = """
¡Hola {nombre}! Bienvenido/a al club oficial de CoesSneakers en Telegram. 🚀👟

Soy Chokolo, tu asistente virtual, y estoy aquí para ayudarte.

Aquí encontrarás:
• Todos los productos y sneakers disponibles.
• La manera más fácil de adquirirlos.
• Las últimas noticias y lanzamientos.

¡Prepárate para explorar lo mejor del mundo sneaker! 

Si necesitas ayuda o tienes preguntas, no dudes en escribirme. 

📌 *Comandos disponibles:*
/price - 📊 Lista de precios.
/size - 📏 Guía de tallas.
/pay - 💳 Métodos de pagos.
/shipments - 🚚 Política de envíos.
/buscar - 🔍 Buscar producto.

¡Que disfrutes tu experiencia sneakers!
"""

MENSAJE_DESPEDIDA = """
👋 ¡{nombre}! Fue un gusto tenerte en la comunidad. Sabemos que las circunstancias cambian.
¡Pero Esperamos verte pronto de nuevo en la familia CoesSneakers!
"""

def agregar_footer(mensaje):
    """Añade el enlace SIN FORMATO para evitar meta descripciones"""
    mensaje = mensaje.replace('[', '').replace(']', '').replace('(', '').replace(')', '')
    return f"{mensaje}\n\n📍 Pagina Web: {SITIO_WEB}"

async def enviar_respuesta(update: Update, texto: str, reply_to: int = None):
    """Función centralizada para enviar respuestas"""
    params = {
        'text': agregar_footer(texto),
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    if reply_to:
        params['reply_to_message_id'] = reply_to
    
    await update.message.reply_text(**params)

# =============================================
# FUNCIONES PRINCIPALES DEL BOT (CON PERSISTENCIA)
# =============================================
async def bienvenida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in GRUPOS_AUTORIZADOS:
            return

        for user in update.message.new_chat_members:
            mensaje_completo = f"{MENSAJE_BIENVENIDA.format(nombre=user.first_name)}\n\n📍 Pagina Web: {SITIO_WEB}"
            await context.bot.send_message(
                chat_id=chat_id,
                text=mensaje_completo,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            logger.info(f"Nuevo miembro en {chat_id}: {user.first_name}")

    except Exception as e:
        logger.error(f"Error en bienvenida: {e}")

async def despedida(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in GRUPOS_AUTORIZADOS:
            return

        user = update.message.left_chat_member
        if user.id != context.bot.id:
            await context.bot.send_message(
                chat_id=chat_id,
                text=MENSAJE_DESPEDIDA.format(nombre=user.first_name),
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error en despedida: {e}")

async def registrar_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in GRUPOS_AUTORIZADOS:
            return

        user = update.effective_user
        admins = await context.bot.get_chat_administrators(chat_id)
        if user.id not in [admin.user.id for admin in admins]:
            return

        if not (update.message.photo and update.message.caption):
            return

        match = PATRON_PRODUCTO.search(update.message.caption)
        if not match:
            await enviar_respuesta(
                update,
                "⚠️ *Formato incorrecto* ⚠️\n\n"
                "Ejemplos válidos:\n"
                "• Nike Air Force 1\nTalla 11 y 10.5 - $95\n"
                "• Jordan Aj 2/3\n11, 10.5 - 95$\n"
                "• New Balance 550\n11 / 10.5 - USD 95\n"
                "• Adidas Samba\n8.0 – 65USD",
                update.message.message_id
            )
            return

        datos = match.groupdict()
        modelo = datos['modelo'].strip()
        precio = re.sub(r'(USD|\$|\s)', '', datos['precio']).strip()  # Normaliza a "65"
        tallas = re.split(r'\s*(?:,|y|\/)\s*', datos['tallas'])

        # Validar y normalizar tallas
        tallas_validas = []
        for talla in tallas:
            try:
                talla = talla.strip()
                talla_float = float(talla)
                tallas_validas.append(f"{talla_float:.1f}" if talla_float.is_integer() else str(talla_float))
            except ValueError:
                await enviar_respuesta(
                    update,
                    f"❌ Talla inválida: '{talla}'. Debe ser un número (ej: 10.5)",
                    update.message.message_id
                )
                return

        # Registrar cada talla
        productos_registrados = []
        for talla in tallas_validas:
            producto_id = f"{modelo.lower()}_{talla}"
            
            productos_db[producto_id] = {
                'modelo': modelo,
                'talla': talla,
                'precio': f"${precio}",
                'foto': update.message.photo[-1].file_id,
                'chat_id': chat_id,
                'msg_id': update.message.message_id,
                'user_id': user.id
            }
            productos_registrados.append(f"{modelo} (Talla {talla})")

        guardar_db()
        hacer_backup()
        
        logger.info(f"📦 Productos registrados: {', '.join(productos_registrados)} | Chat ID: {chat_id}")

        await enviar_respuesta(
            update,
            f"✅ *Productos registrados:*\n"
            f"👟 *Modelo:* {modelo}\n"
            f"📏 *Tallas:* {', '.join(tallas_validas)} US\n"
            f"💵 *Precio:* ${precio}",
            update.message.message_id
        )

    except Exception as e:
        logger.error(f"Error registrando producto: {e}")
        await enviar_respuesta(
            update,
            "❌ Error al registrar el producto. Verifica el formato e intenta nuevamente.",
            update.message.message_id
        )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        productos_grupo = [p for p in productos_db.values() if p['chat_id'] == chat_id]

        if not productos_grupo:
            await enviar_respuesta(
                update,
                "🛒 *No hay productos registrados aún*\n\n"
                "Los administradores deben publicar los productos con foto y descripción."
            )
            return

        respuesta = "💰 *Lista de Precios* 💰\n\n"
        for p in productos_grupo:
            respuesta += f"▪️ *{p['modelo']}*: {p['precio']}\n"

        await enviar_respuesta(update, respuesta)

    except Exception as e:
        logger.error(f"Error en /price: {e}")
        await enviar_respuesta(update, "❌ Error al obtener precios")

async def size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        productos_grupo = [p for p in productos_db.values() if p['chat_id'] == chat_id]

        if not productos_grupo:
            await enviar_respuesta(update, "📏 *No hay tallas registradas*")
            return

        respuesta = "👟 *Tallas Disponibles* (US) 👟\n\n"
        for p in productos_grupo:
            respuesta += f"▪️ *{p['modelo']}*: {p['talla']}\n"

        await enviar_respuesta(update, respuesta)

    except Exception as e:
        logger.error(f"Error en /size: {e}")
        await enviar_respuesta(update, "❌ Error al obtener tallas")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        respuesta = """💳 *Métodos de Pago Aceptados* 💳

• PayPal (+5% comisión) 📱.
• Zelle 🏦.
• Binance (USDT) 🪙.
• Efectivo (En las Oficinas de Coessneakers LLC) 💵.

⚠️ Siempre confirma disponibilidad antes de pagar ⚠️
⚠️ Enviar comprobante de Pago a @ElCoesSneakers ⚠️"""
        
        await enviar_respuesta(update, respuesta)

    except Exception as e:
        logger.error(f"Error en /pay: {e}")

async def shipments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        respuesta = """🚚 *Política de Envíos* 🚚

• 🇺🇸 EEUU: USPS 3-5 días.
• 🌎 Internacional: 🇻🇪 Venezuela / 🇨🇴 Colombia / 🇦🇷 Argentina / 🇨🇱 Chile: Debes tener casillero en EE.UU con tu Agencia de envío de tu preferencia a tu país.
⚠️ (El producto se entregará en dicha dirección para que luego sea canalizado el envío a la dirección que tengas registrada) ⚠️.

📦 Todos los envíos incluyen:
- Caja original.
- Seguimiento."""
        
        await enviar_respuesta(update, respuesta)

    except Exception as e:
        logger.error(f"Error en /shipments: {e}")

async def buscar_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        
        if not context.args:
            await enviar_respuesta(
                update,
                "🔍 *Uso:* /buscar [modelo]\nEjemplo: /buscar New Balance"
            )
            return

        query = ' '.join(context.args).lower().strip()
        resultados = [
            p for p in productos_db.values() 
            if (query in p['modelo'].lower() and p['chat_id'] == chat_id)
        ]

        if not resultados:
            await enviar_respuesta(
                update,
                f"🔍 No se encontró '{query}'\n\nPrueba con menos palabras"
            )
            return

        for producto in resultados:
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=producto['foto'],
                    caption=agregar_footer(
                        f"👟 *{producto['modelo']}*\n"
                        f"📏 Talla: {producto['talla']} US\n"
                        f"💵 Precio: {producto['precio']}"
                    ),
                    parse_mode='Markdown',
                    reply_to_message_id=producto['msg_id']
                )
            except Exception as e:
                logger.error(f"Error mostrando producto: {e}")
                await enviar_respuesta(
                    update,
                    f"👟 *{producto['modelo']}*\n"
                    f"📏 Talla: {producto['talla']} US\n"
                    f"💵 Precio: {producto['precio']}"
                )

    except Exception as e:
        logger.error(f"Error en /buscar: {e}")
        await enviar_respuesta(
            update,
            "❌ Error en la búsqueda. Verifica el formato e intenta nuevamente."
        )

async def eliminar_producto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Verificar permisos de administrador
        admins = await context.bot.get_chat_administrators(chat_id)
        if user.id not in [admin.user.id for admin in admins]:
            await enviar_respuesta(update, "❌ Solo administradores pueden eliminar productos")
            return

        if not context.args:
            await enviar_respuesta(
                update,
                "⚠️ Uso: /eliminar [modelo] [talla]\n"
                "Ejemplos:\n"
                "/eliminar New Balance 1010 talla 7.5\n"
                "/eliminar New Balance 1010 7.5\n"
                "/eliminar \"Nike Air Force 1\" 10.5"
            )
            return

        # Unir todos los argumentos y procesar
        full_text = ' '.join(context.args)
        
        # Patrón para detectar talla al final (7.5, 10, etc.)
        talla_match = re.search(r'(?:talla\s*)?(\d+\.?\d*)$', full_text, re.IGNORECASE)
        
        if not talla_match:
            await enviar_respuesta(
                update,
                "❌ Debes especificar una talla válida al final\n"
                "Ejemplo: /eliminar New Balance 1010 7.5",
                update.message.message_id
            )
            return

        talla = talla_match.group(1)
        modelo = full_text[:talla_match.start()].strip()
        
        # Normalizar talla (11 -> 11.0 para coincidir con el formato de registro)
        try:
            talla_float = float(talla)
            talla_normalizada = f"{talla_float:.1f}" if talla_float.is_integer() else str(talla_float)
        except ValueError:
            await enviar_respuesta(
                update,
                f"❌ Talla inválida: '{talla}'. Debe ser un número (ej: 10.5)",
                update.message.message_id
            )
            return

        # Buscar producto por ID compuesto (modelo_normalizado + talla)
        modelo_normalizado = modelo.lower().strip('"\'')
        producto_id = f"{modelo_normalizado}_{talla_normalizada}"
        
        if producto_id in productos_db:
            producto = productos_db[producto_id]
            del productos_db[producto_id]
            
            guardar_db()
            hacer_backup()
            
            await enviar_respuesta(
                update,
                f"🗑️ *Producto eliminado:*\n"
                f"👟 *Modelo:* {producto['modelo']}\n"
                f"📏 *Talla:* {producto['talla']} US\n"
                f"💵 *Precio:* {producto['precio']}",
                update.message.message_id
            )
            logger.info(f"Producto eliminado: {producto_id} | Por: {user.first_name}")
        else:
            # Mostrar sugerencias si no se encuentra exactamente
            productos_similares = [
                p for p in productos_db.values() 
                if modelo_normalizado in p['modelo'].lower() and p['chat_id'] == chat_id
            ]
            
            if productos_similares:
                tallas_disponibles = list(set(p['talla'] for p in productos_similares))
                modelos_similares = list(set(p['modelo'] for p in productos_similares))
                
                mensaje = (
                    f"❌ No se encontró '{modelo}' en talla {talla_normalizada}\n\n"
                    f"📝 *Modelos similares:* {', '.join(modelos_similares[:3])}\n"
                    f"📏 *Tallas disponibles:* {', '.join(tallas_disponibles)}"
                )
            else:
                mensaje = f"❌ No se encontró el producto '{modelo}'"
                
            await enviar_respuesta(
                update,
                mensaje,
                update.message.message_id
            )

    except Exception as e:
        logger.error(f"Error eliminando producto: {e}")
        await enviar_respuesta(
            update,
            "❌ Error al eliminar el producto. Intenta nuevamente.",
            update.message.message_id
        )

# =============================================
# CONFIGURACIÓN Y EJECUCIÓN DEL BOT
# =============================================
def main():
    try:
        print("🔄 Iniciando bot...")
        print(f"📦 Productos cargados: {len(productos_db)}")
        
        # Configurar el bot de Telegram
        app = ApplicationBuilder().token(TOKEN).build()

        # Handlers para eventos
        app.add_handler(MessageHandler(
            filters.Chat(GRUPOS_AUTORIZADOS) & filters.StatusUpdate.NEW_CHAT_MEMBERS,
            bienvenida
        ))
        app.add_handler(MessageHandler(
            filters.Chat(GRUPOS_AUTORIZADOS) & filters.StatusUpdate.LEFT_CHAT_MEMBER,
            despedida
        ))

        # Handlers para comandos
        app.add_handler(CommandHandler("eliminar", eliminar_producto))
        app.add_handler(CommandHandler("price", price))
        app.add_handler(CommandHandler("size", size))
        app.add_handler(CommandHandler("pay", pay))
        app.add_handler(CommandHandler("shipments", shipments))
        app.add_handler(CommandHandler("buscar", buscar_producto))

        # Handler para productos
        app.add_handler(MessageHandler(
            filters.Chat(GRUPOS_AUTORIZADOS) & filters.PHOTO,
            registrar_producto
        ))

        logger.info("Bot iniciado correctamente")
        print(f"✅ Bot de Coes Sneakers listo | Web: {SITIO_WEB}")

        # Iniciar Flask en un hilo separado
        import threading
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # Iniciar el bot de Telegram
        app.run_polling()

    except Exception as e:
        logger.critical(f"Error al iniciar bot: {e}")
        print(f"❌ Error crítico: {e}")

if __name__ == '__main__':
    main()