import telebot
from threading import Thread
import time
from datetime import datetime
import pytz
import json
from flask import Flask, request
import os
from typing import Dict, List
import logging

# =============================================
# НАСТРОЙКА ЭТИХ ЗНАЧЕНИЙ ОБЯЗАТЕЛЬНА В RAILWAY
# =============================================
# В Railway перейдите в Settings -> Variables и добавьте:
#
# 1. TOKEN - токен вашего бота от BotFather
# 2. WEBHOOK_URL - URL вашего приложения в Railway (например: https://your-app-name.up.railway.app)
# 3. PORT - оставьте как есть (8080)
# 4. STATE_FILE_PATH - оставьте как есть ('/tmp/bot_state.json')
# =============================================

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variable validation
TOKEN = os.environ.get('TOKEN')
if not TOKEN:
    raise ValueError("No TOKEN environment variable set")

WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
if not WEBHOOK_URL:
    raise ValueError("No WEBHOOK_URL environment variable set")

# Initialize bot and Flask
try:
    bot = telebot.TeleBot(TOKEN)
    app = Flask(__name__)
except Exception as e:
    logger.critical(f"Failed to initialize bot or Flask: {e}")
    raise

# =============================================
# НАСТРОЙТЕ СООБЩЕНИЯ ПОД СЕБЯ (ОПЦИОНАЛЬНО)
# =============================================
WATER_MESSAGES = [
    "Пора пить водичку! 💧 Не забывай о себе заботиться!",
    "Время выпить стакан воды! 🌊 Твое здоровье важно!",
    "Напоминаю про водичку! 💦 Сделай небольшой перерыв!",
    "Выпей водички! 🚰 Это полезно для тебя!",
    "Пора увлажниться! 💧 Вода - источник жизни!",
    "Не забудь про водичку! 🌊 Твое тело скажет спасибо!"
]

TABLET_MESSAGE = "Милая, пора принять таблетку! 💊 Не забывай о своем здоровье! ❤️"

# =============================================
# НАСТРОЙТЕ ЧАСЫ НАПОМИНАНИЙ (ОПЦИОНАЛЬНО)
# По умолчанию каждые 2 часа с 10 до 20
# =============================================
REMINDER_HOURS = [10, 12, 14, 16, 18, 20]


# =============================================

class UserState:
    def __init__(self):
        self.water_reminders: Dict[int, Dict[str, bool]] = {}
        self.tablet_reminder: Dict[int, bool] = {}
        self.chat_ids: List[int] = []

    def add_user(self, chat_id: int) -> None:
        try:
            if chat_id not in self.chat_ids:
                self.chat_ids.append(chat_id)
                self.water_reminders[chat_id] = {}
                self.tablet_reminder[chat_id] = False
                self.save_state()
                logger.info(f"Added new user with chat_id: {chat_id}")
        except Exception as e:
            logger.error(f"Error adding user {chat_id}: {e}")

    def save_state(self) -> None:
        try:
            state = {
                'chat_ids': self.chat_ids,
                'water_reminders': self.water_reminders,
                'tablet_reminder': self.tablet_reminder
            }
            file_path = os.environ.get('STATE_FILE_PATH', '/tmp/bot_state.json')
            with open(file_path, 'w') as f:
                json.dump(state, f)
            logger.info(f"State saved successfully to {file_path}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def load_state(self) -> None:
        try:
            file_path = os.environ.get('STATE_FILE_PATH', '/tmp/bot_state.json')
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    state = json.load(f)
                    self.chat_ids = state.get('chat_ids', [])
                    self.water_reminders = {int(k): v for k, v in state.get('water_reminders', {}).items()}
                    self.tablet_reminder = {int(k): v for k, v in state.get('tablet_reminder', {}).items()}
                logger.info(f"State loaded successfully. Active users: {len(self.chat_ids)}")
            else:
                logger.warning(f"State file not found at {file_path}. Starting with empty state.")
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            self.chat_ids = []
            self.water_reminders = {}
            self.tablet_reminder = {}


# Initialize state
state = UserState()


def is_weekday():
    return datetime.now(pytz.timezone('Europe/Moscow')).weekday() < 5


def create_water_markup(hour: int):
    markup = telebot.types.InlineKeyboardMarkup()
    button = telebot.types.InlineKeyboardButton(
        "✅ Выпила воду",
        callback_data=f"water_confirm_{hour}"
    )
    markup.add(button)
    return markup


def create_tablet_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    button = telebot.types.InlineKeyboardButton(
        "✅ Таблетку выпила",
        callback_data="tablet_confirm"
    )
    markup.add(button)
    return markup


def send_water_reminder(chat_id: int, hour: int) -> None:
    try:
        if str(hour) not in state.water_reminders.get(chat_id, {}):
            state.water_reminders[chat_id][str(hour)] = False

        if not state.water_reminders[chat_id][str(hour)]:
            message = WATER_MESSAGES[hour % len(WATER_MESSAGES)]
            bot.send_message(chat_id, message)
            bot.send_message(
                chat_id,
                "Подтверди, что выпила водичку:",
                reply_markup=create_water_markup(hour)
            )
            logger.info(f"Water reminder sent to {chat_id} for hour {hour}")
    except Exception as e:
        logger.error(f"Error sending water reminder to {chat_id}: {e}")


def send_tablet_reminder(chat_id: int) -> None:
    try:
        if not state.tablet_reminder.get(chat_id, False):
            bot.send_message(
                chat_id,
                TABLET_MESSAGE,
                reply_markup=create_tablet_markup()
            )
            logger.info(f"Tablet reminder sent to {chat_id}")
    except Exception as e:
        logger.error(f"Error sending tablet reminder to {chat_id}: {e}")


def reset_daily_state():
    try:
        for chat_id in state.chat_ids:
            state.water_reminders[chat_id] = {}
            state.tablet_reminder[chat_id] = False
        state.save_state()
        logger.info("Daily state reset complete")
    except Exception as e:
        logger.error(f"Error resetting daily state: {e}")


# =============================================
# НАСТРОЙТЕ ПРИВЕТСТВЕННОЕ СООБЩЕНИЕ (ОПЦИОНАЛЬНО)
# =============================================
@bot.message_handler(commands=['start'])
def start(message):
    try:
        chat_id = message.chat.id
        state.add_user(chat_id)
        bot.reply_to(
            message,
            "Котка, привет! Я тебя очень люблю ❤️\n\n"
            "Я буду следить, чтобы ты пила водичку каждые 2 часа в будние дни!\n\n"
            "Не забывай подтверждать, когда попьешь 😊"
        )
        logger.info(f"New user started bot: {chat_id}")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")


@bot.message_handler(commands=['status'])
def status(message):
    try:
        chat_id = message.chat.id
        bot.reply_to(
            message,
            f"Бот активен!\nТекущих пользователей: {len(state.chat_ids)}\n"
            f"Ваш chat_id: {chat_id}"
        )
    except Exception as e:
        logger.error(f"Error in status handler: {e}")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data.startswith('water_confirm_'):
            hour = call.data.split('_')[2]
            chat_id = call.message.chat.id
            state.water_reminders[chat_id][str(hour)] = True
            state.save_state()
            bot.answer_callback_query(call.id, "Отлично! Продолжай в том же духе! 💪")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

        elif call.data == 'tablet_confirm':
            chat_id = call.message.chat.id
            state.tablet_reminder[chat_id] = True
            state.save_state()
            bot.answer_callback_query(call.id, "Молодец! Таблетка принята! 💊")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")


def reminder_thread():
    logger.info("Reminder thread started")
    last_day = -1

    while True:
        try:
            current_time = datetime.now(pytz.timezone('Europe/Moscow'))

            if current_time.day != last_day:
                reset_daily_state()
                last_day = current_time.day

            if is_weekday():
                hour = current_time.hour
                minute = current_time.minute

                if hour in REMINDER_HOURS and minute == 0:
                    logger.info(f"Sending scheduled reminders for hour {hour}")
                    for chat_id in state.chat_ids:
                        try:
                            send_water_reminder(chat_id, hour)
                            if hour == 12:  # Время приема таблетки
                                send_tablet_reminder(chat_id)
                        except Exception as e:
                            logger.error(f"Error sending reminders to {chat_id}: {e}")
                            continue

                # Повторные напоминания
                if minute % 10 == 0:
                    for chat_id in state.chat_ids:
                        if str(hour) in state.water_reminders.get(chat_id, {}) and \
                                not state.water_reminders[chat_id][str(hour)]:
                            send_water_reminder(chat_id, hour)

                if hour >= 12 and minute % 30 == 0:
                    for chat_id in state.chat_ids:
                        if not state.tablet_reminder.get(chat_id, False):
                            send_tablet_reminder(chat_id)

            time.sleep(60)
        except Exception as e:
            logger.error(f"Error in reminder thread: {e}")
            time.sleep(5)


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            if update is None:
                logger.error("Received invalid update")
                return 'Invalid update', 400
            bot.process_new_updates([update])
            return '', 200
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return 'Error processing update', 500
    else:
        logger.warning("Received non-JSON request")
        return 'Content-type must be application/json', 400


@app.route('/health', methods=['GET'])
def health_check():
    return 'Bot is running!', 200


if __name__ == "__main__":
    try:
        # Load state
        state.load_state()

        # Start reminder thread
        reminder_thread = Thread(target=reminder_thread)
        reminder_thread.daemon = True
        reminder_thread.start()

        # Set up webhook
        bot.remove_webhook()
        webhook_url = f'{WEBHOOK_URL.rstrip("/")}/{TOKEN}'
        if not webhook_url.startswith('https://'):
            raise ValueError("Webhook URL must use HTTPS")

        webhook_info = bot.set_webhook(url=webhook_url)
        if not webhook_info:
            raise ValueError("Failed to set webhook")

        logger.info(f"Webhook set to {webhook_url}")

        # Start Flask app
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port)

    except Exception as e:
        logger.critical(f"Critical error starting the bot: {e}")
        raise