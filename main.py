import telebot
from threading import Thread
import time
from datetime import datetime
import pytz
import json
from flask import Flask, request
import os
from typing import Dict, List

# Токен бота
TOKEN = '7598457393:AAGYDyzb67hgudu1e1wPiqet0imV-F6ZCiI'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)


# Структуры данных для хранения состояния пользователей
class UserState:
    def __init__(self):
        self.water_reminders: Dict[int, Dict[str, bool]] = {}  # chat_id -> {hour: confirmed}
        self.tablet_reminder: Dict[int, bool] = {}  # chat_id -> confirmed
        self.chat_ids: List[int] = []

    def add_user(self, chat_id: int) -> None:
        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            self.water_reminders[chat_id] = {}
            self.tablet_reminder[chat_id] = False
            self.save_state()

    def save_state(self) -> None:
        state = {
            'chat_ids': self.chat_ids,
            'water_reminders': self.water_reminders,
            'tablet_reminder': self.tablet_reminder
        }
        with open('bot_state.json', 'w') as f:
            json.dump(state, f)

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
        except (FileNotFoundError, json.JSONDecodeError):
            self.chat_ids = []
            self.water_reminders = {}
            self.tablet_reminder = {}


# Создаем глобальный объект состояния
state = UserState()

WATER_MESSAGES = [
    "Котка, пора сделать пару глоточков воды! 💧",
    "Проверь, полный ли у тебя стакан. Если нет, то попроси меня, если я дома. Я принесу и надо будет попить💧",
    "Любочка, водичка стоит возле тебя и надо попить!💧",
    "Время оторваться от работы, немного выдохнуть и попить воды! 💧",
    "Если сейчас попить воды, то твой любимый котка станет счастливее! 💧",
    "Кота, не жульничай! Сделай глоточек и нажми на кнопку💧"
]

TABLET_MESSAGE = "А ещё, котка, уже время выпить таблетку! Попроси меня и я принесу 💊"


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


def send_tablet_reminder(chat_id: int) -> None:
    if not state.tablet_reminder.get(chat_id, False):
        bot.send_message(
            chat_id,
            TABLET_MESSAGE,
            reply_markup=create_tablet_markup()
        )


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    state.add_user(chat_id)
    bot.reply_to(
        message,
        "Котка, привет! Я тебя очень люблю ❤️\n\n"
        "Я буду следить, чтобы ты пила водичку каждые 2 часа в будние дни!\n\n"
        "Не забывай подтверждать, когда попьешь 😊"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("water_confirm_"))
def water_confirmation(call):
    chat_id = call.message.chat.id
    hour = call.data.split("_")[-1]

    if chat_id in state.water_reminders:
        state.water_reminders[chat_id][hour] = True
        state.save_state()

    bot.answer_callback_query(call.id)
    bot.send_message(chat_id, "Ты у меня самая лучшая! 😊")


@bot.callback_query_handler(func=lambda call: call.data == "tablet_confirm")
def tablet_confirmation(call):
    chat_id = call.message.chat.id
    state.tablet_reminder[chat_id] = True
    state.save_state()

    bot.answer_callback_query(call.id)
    bot.send_message(chat_id, "Просто умничка! Не забудь отметить в своём приложении 😊")


def reset_daily_state():
    """Сброс состояния напоминаний в начале каждого дня"""
    for chat_id in state.chat_ids:
        state.water_reminders[chat_id] = {}
        state.tablet_reminder[chat_id] = False
    state.save_state()


def reminder_thread():
    last_day = -1

    while True:
        current_time = datetime.now(pytz.timezone('Europe/Moscow'))

        # Сброс состояния в начале нового дня
        if current_time.day != last_day:
            reset_daily_state()
            last_day = current_time.day

        if is_weekday():
            hour = current_time.hour
            minute = current_time.minute

            if hour in [10, 12, 14, 16, 18, 20] and minute == 0:
                for chat_id in state.chat_ids:
                    try:
                        send_water_reminder(chat_id, hour)
                        if hour == 12:
                            send_tablet_reminder(chat_id)
                    except telebot.apihelper.ApiException as e:
                        print(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")

            # Повторные напоминания
            if minute % 10 == 0:  # Каждые 10 минут
                for chat_id in state.chat_ids:
                    if str(hour) in state.water_reminders.get(chat_id, {}) and \
                            not state.water_reminders[chat_id][str(hour)]:
                        try:
                            send_water_reminder(chat_id, hour)
                        except telebot.apihelper.ApiException as e:
                            print(f"Ошибка отправки напоминания о воде пользователю {chat_id}: {e}")

            if hour >= 12 and minute % 30 == 0:  # Каждые 30 минут после 12:00
                for chat_id in state.chat_ids:
                    if not state.tablet_reminder.get(chat_id, False):
                        try:
                            send_tablet_reminder(chat_id)
                        except telebot.apihelper.ApiException as e:
                            print(f"Ошибка отправки напоминания о таблетке пользователю {chat_id}: {e}")

        time.sleep(60)


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return ''
    return 'ok'


if __name__ == "__main__":
    state.load_state()

    reminder_thread = Thread(target=reminder_thread, daemon=True)
    reminder_thread.start()

    bot.remove_webhook()
    bot.set_webhook(url=f'https://vita-bot.up.railway.app/{TOKEN}')

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)