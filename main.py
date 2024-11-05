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

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
TOKEN = '7598457393:AAGYDyzb67hgudu1e1wPiqet0imV-F6ZCiI'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# Структуры данных для хранения состояния пользователей
class UserState:
    def __init__(self):
        self.water_reminders: Dict[int, Dict[str, bool]] = {}
        self.tablet_reminder: Dict[int, bool] = {}
        self.chat_ids: List[int] = []

    def add_user(self, chat_id: int) -> None:
        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            self.water_reminders[chat_id] = {}
            self.tablet_reminder[chat_id] = False
            self.save_state()
            logger.info(f"Added new user with chat_id: {chat_id}")

    def save_state(self) -> None:
        try:
            state = {
                'chat_ids': self.chat_ids,
                'water_reminders': self.water_reminders,
                'tablet_reminder': self.tablet_reminder
            }
            with open('bot_state.json', 'w') as f:
                json.dump(state, f)
            logger.info("State saved successfully")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def load_state(self) -> None:
        try:
            with open('bot_state.json', 'r') as f:
                state = json.load(f)
                self.chat_ids = state.get('chat_ids', [])
                self.water_reminders = state.get('water_reminders', {})
                self.tablet_reminder = state.get('tablet_reminder', {})

                # Конвертируем строковые ключи в целые числа
                self.water_reminders = {int(k): v for k, v in self.water_reminders.items()}
                self.tablet_reminder = {int(k): v for k, v in self.tablet_reminder.items()}
            logger.info(f"State loaded successfully. Active users: {len(self.chat_ids)}")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load state: {e}. Starting with empty state.")
            self.chat_ids = []
            self.water_reminders = {}
            self.tablet_reminder = {}


# Создаем глобальный объект состояния
state = UserState()


# Ваши существующие константы WATER_MESSAGES и TABLET_MESSAGE остаются без изменений...

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


def reminder_thread():
    logger.info("Reminder thread started")
    last_day = -1

    while True:
        try:
            current_time = datetime.now(pytz.timezone('Europe/Moscow'))

            # Сброс состояния в начале нового дня
            if current_time.day != last_day:
                reset_daily_state()
                last_day = current_time.day
                logger.info(f"Daily state reset for day {current_time.day}")

            if is_weekday():
                hour = current_time.hour
                minute = current_time.minute

                if hour in [10, 12, 14, 16, 18, 20] and minute == 0:
                    logger.info(f"Sending scheduled reminders for hour {hour}")
                    for chat_id in state.chat_ids:
                        send_water_reminder(chat_id, hour)
                        if hour == 12:
                            send_tablet_reminder(chat_id)

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
            time.sleep(60)  # Даже при ошибке продолжаем работу


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        try:
            update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
            bot.process_new_updates([update])
            logger.info("Webhook request processed successfully")
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
        return ''
    return 'ok'


@app.route('/health', methods=['GET'])
def health_check():
    return 'Bot is running!', 200


if __name__ == "__main__":
    try:
        state.load_state()

        # Запускаем поток с напоминаниями
        reminder_thread = Thread(target=reminder_thread)
        reminder_thread.daemon = False  # Важное изменение!
        reminder_thread.start()

        # Настраиваем вебхук
        bot.remove_webhook()
        bot.set_webhook(url=f'https://vita-bot.up.railway.app/{TOKEN}')

        # Запускаем Flask приложение
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error starting the bot: {e}")