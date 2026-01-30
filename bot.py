import os
import logging
import asyncio
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)


import database
from openia import preguntar_gpt


load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ADD_TASK, DELETE_TASK, EDIT_TASK_ID, EDIT_TASK_TEXT = range(4)

CB_ADD = "add"
CB_LIST = "list"
CB_EDIT = "edit"
CB_DELETE = "delete"
CB_ORDER = "order"


async def run_sync(func, *args):
    """Ejecuta funciones bloqueantes sin congelar el bot."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)


def menu_principal():
   
    keyboard = [
        [InlineKeyboardButton("✨ Nueva Tarea", callback_data=CB_ADD)],
        [
            InlineKeyboardButton("📂 Mis Tareas", callback_data=CB_LIST),
            InlineKeyboardButton("🧠 Priorizar (IA)", callback_data=CB_ORDER)
        ],
        [
            InlineKeyboardButton("✏️ Editar", callback_data=CB_EDIT),
            InlineKeyboardButton("🗑️ Eliminar", callback_data=CB_DELETE)
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**Gestor de Tareas**\nSeleccione una acción para comenzar:",
        reply_markup=menu_principal(),
        parse_mode="Markdown"
    )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Acción cancelada.",
        reply_markup=menu_principal()
    )
    return ConversationHandler.END

async def botones_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data

    try:
        if data == CB_ADD:
            await query.message.reply_text("Escriba la descripción de la tarea (o /cancel):")
            return ADD_TASK

        elif data == CB_LIST:
            tasks = await run_sync(database.get_tasks, user_id)
            if not tasks:
                await query.message.reply_text("La lista de tareas está vacía.")
            else:
                context.user_data["map_ids"] = {i: t[0] for i, t in enumerate(tasks, start=1)}
                msg = "**Tareas Pendientes:**\n\n"
                msg += "\n".join([f"`{i}.` {t[1]}" for i, t in enumerate(tasks, start=1)])
                await query.message.reply_text(msg, parse_mode="Markdown")
            
            await query.message.reply_text("Menú principal:", reply_markup=menu_principal())
            return ConversationHandler.END

        elif data == CB_DELETE:
            await query.message.reply_text("Ingrese el número de la tarea a eliminar:")
            return DELETE_TASK

        elif data == CB_EDIT:
            tasks = await run_sync(database.get_tasks, user_id)
            if not tasks:
                await query.message.reply_text("No hay tareas para editar.")
                return ConversationHandler.END

            context.user_data["map_ids"] = {i: t[0] for i, t in enumerate(tasks, start=1)}
            msg = "**Seleccione el número de tarea para editar:**\n\n"
            msg += "\n".join([f"`{i}.` {t[1]}" for i, t in enumerate(tasks, start=1)])
            
            await query.message.reply_text(msg, parse_mode="Markdown")
            return EDIT_TASK_ID

        elif data == CB_ORDER:
            tasks = await run_sync(database.get_tasks, user_id)
            if not tasks:
                await query.message.reply_text("No hay tareas para procesar.")
            else:
                msg_wait = await query.message.reply_text("Analizando con inteligencia artificial...")
                tareas_texto = "\n".join([f"- {t[1]}" for t in tasks])
                prompt = f"Prioriza estas tareas por importancia y dificultad:\n{tareas_texto}"
                
                try:
                    respuesta = await run_sync(preguntar_gpt, prompt)
                    await context.bot.edit_message_text(
                        chat_id=query.message.chat_id,
                        message_id=msg_wait.message_id,
                        text=f"**Sugerencia de la IA:**\n\n{respuesta}",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Error IA: {e}")
                    await query.message.reply_text("No se pudo conectar con el servicio de IA.")

            await query.message.reply_text("Menú principal:", reply_markup=menu_principal())
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error: {e}")
        await query.message.reply_text("Error en el sistema.")
        return ConversationHandler.END


# LÓGICA DE CRUD

async def guardar_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        await run_sync(database.add_task, user_id, update.message.text)
        await update.message.reply_text("Tarea registrada correctamente.")
    except Exception as e:
        logger.error(f"DB Error: {e}")
        await update.message.reply_text("Error al guardar.")

    await update.message.reply_text("Menú principal:", reply_markup=menu_principal())
    return ConversationHandler.END

async def eliminar_tarea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        numero = int(update.message.text)
        real_id = context.user_data.get("map_ids", {}).get(numero)
        
        if not real_id:
            await update.message.reply_text("Número de tarea no válido.")
            return DELETE_TASK

        await run_sync(database.delete_task, update.message.from_user.id, real_id)
        await update.message.reply_text("Tarea eliminada.")
    except ValueError:
        await update.message.reply_text("Por favor, ingrese solo el número.")
        return DELETE_TASK

    await update.message.reply_text("Menú principal:", reply_markup=menu_principal())
    return ConversationHandler.END

async def recibir_id_editar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        numero = int(update.message.text)
        real_id = context.user_data.get("map_ids", {}).get(numero)
        
        if not real_id:
            await update.message.reply_text("Número inválido.")
            return EDIT_TASK_ID

        context.user_data["edit_id"] = real_id
        await update.message.reply_text("Ingrese el nuevo texto para la tarea:")
        return EDIT_TASK_TEXT
    except ValueError:
        await update.message.reply_text("Ingrese un número válido.")
        return EDIT_TASK_ID

async def guardar_edicion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await run_sync(database.update_task, update.message.from_user.id, context.user_data.get("edit_id"), update.message.text)
        await update.message.reply_text("Tarea actualizada con éxito.")
    except Exception as e:
        logger.error(f"DB Update Error: {e}")
        await update.message.reply_text("Error al actualizar.")

    await update.message.reply_text("Menú principal:", reply_markup=menu_principal())
    return ConversationHandler.END


# MAIN

def main():
    if not BOT_TOKEN:
        logger.critical("Falta BOT_TOKEN")
        return

    database.init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(botones_menu)],
        states={
            ADD_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_tarea)],
            DELETE_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, eliminar_tarea)],
            EDIT_TASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_id_editar)],
            EDIT_TASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_edicion)],
        },
        fallbacks=[CommandHandler("cancel", cancelar)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    logger.info("Bot en línea.")
    app.run_polling()

if __name__ == "__main__":
    main()