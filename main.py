import telebot
from threading import Thread
from datetime import datetime
import pytz
import json
import os
import time
from flask import Flask, request

# Ваш токен от BotFather
TOKEN = '7598457393:AAGYDyzb67hgudu1e1wPiqet0imV-F6ZCiI'

# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

# Flask сервер для обработки вебхуков
app = Flask(__name__)

# Глобальные переменные для хранения состояний пользователей
user_states = {}
paused = False
chat_ids = []

# Сообщения-напоминания
reminder_messages = [
    "Котка, пора сделать пару глоточков воды! 💧",
    "Проверь, полный ли у тебя стакан. Если нет, то попроси меня, если я дома. Я принесу и надо будет попить💧",
    "Любочка, водичка стоит возле тебя и надо попить!💧",
    "Время оторваться от работы, немного выдохнуть и попить воды! 💧",
    "Если сейчас попить воды, то твой любимый котка станет счастливее! 💧",
    "Кота, не жульничай! Сделай глоточек и нажми на кнопку💧"
]

# Сообщение о таблетке
tablet_message = "А ещё, котка, уже время выпить таблетку! Попроси меня и я принесу 💊"

# Флаги для напоминаний
water_reminder_sent = False  # Флаг для напоминания о воде
tablet_reminder_sent = False  # Флаг для напоминания о таблетке


# Функция для загрузки состояния пользователей и чатов
def load_user_states():
    global user_states, chat_ids
    try:
        with open('user_state.json', 'r') as f:
            user_states = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        user_states = {}

    try:
        with open('chat_ids.json', 'r') as f:
            chat_ids = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        chat_ids = []


# Функция для сохранения состояния пользователей и чатов
def save_user_states():
    with open('user_state.json', 'w') as f:
        json.dump(user_states, f)
    with open('chat_ids.json', 'w') as f:
        json.dump(chat_ids, f)


# Проверка, будний ли день
def is_weekday():
    return datetime.now().weekday() < 5  # 0-4 - будние дни


# Запуск напоминаний
def start_reminders():
    while True:
        if not paused and is_weekday():
            current_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
            if current_time in ["10:00", "12:00", "14:00", "15:20", "16:00", "18:00", "20:00"]:
                send_water_reminder()
                if current_time == "12:00":
                    send_tablet_reminder()
        time.sleep(60)  # Проверяем каждую минуту


# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    global paused
    chat_id = message.chat.id
    paused = False

    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        save_user_states()  # Сохраняем список чатов

    bot.send_message(chat_id, "Котка, привет! Я тебя очень люблю ❤️\n\n"
                              "Я стараюсь следить за тем, чтобы ты чаще пила водичку, но подумал, что могу выйти из дома, быть на тренировке или заработаться, или заучиться.\n\n"
                              "Поэтому я специально написал этот телеграм бота, который будет напоминать тебе об этом!\n\n"
                              "Каждый будний день с 10 до 8 вечера он каждые 2 часа будет отправлять тебе напоминание о том, что пора сделать хотя бы пару глоточков) Надо только подтвердить, что ты попила. Но не жульничай!!!\n\n"
                              "А если ты будешь его игнорировать (а не надо), то каждые 10 минут он будет напоминать тебе)")

    # Запускаем поток с напоминаниями
    Thread(target=start_reminders).start()


# Команда /pause
@bot.message_handler(commands=['pause'])
def pause_reminders(message):
    global paused
    paused = True
    bot.send_message(message.chat.id, "Напоминания приостановлены. Используй команду /start, чтобы возобновить.")


# Функция для отправки напоминания о воде
def send_water_reminder():
    global water_reminder_sent
    if not water_reminder_sent:
        for chat_id in chat_ids:
            message = reminder_messages[datetime.now().hour % len(reminder_messages)]
            bot.send_message(chat_id, message)
            markup = telebot.types.InlineKeyboardMarkup()
            confirm_button = telebot.types.InlineKeyboardButton("✅ Выпила воду", callback_data="confirm_water")
            markup.add(confirm_button)
            bot.send_message(chat_id, "Не жульничай, солнышко. Нажми тогда, когда выпила водички", reply_markup=markup)
        water_reminder_sent = True  # Установить флаг, что напоминание отправлено

        # Запуск таймера для повторного напоминания
        Thread(target=repeat_water_reminder).start()


# Функция для повторного напоминания
def repeat_water_reminder():
    time.sleep(600)  # Ждем 10 минут
    for chat_id in chat_ids:
        message = reminder_messages[datetime.now().hour % len(reminder_messages)]
        bot.send_message(chat_id, message)
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Выпила воду", callback_data="confirm_water")
        markup.add(confirm_button)
        bot.send_message(chat_id, "Выпила?", reply_markup=markup)

    # Сбрасываем флаг после повторного напоминания
    global water_reminder_sent
    water_reminder_sent = False


# Функция для отправки напоминания о таблетке
def send_tablet_reminder():
    global tablet_reminder_sent
    if not tablet_reminder_sent:
        for chat_id in chat_ids:
            markup = telebot.types.InlineKeyboardMarkup()
            confirm_button = telebot.types.InlineKeyboardButton("✅ Таблетку выпила", callback_data="confirm_tablet")
            markup.add(confirm_button)
            bot.send_message(chat_id, tablet_message, reply_markup=markup)
        tablet_reminder_sent = True  # Установить флаг, что напоминание отправлено


# Обработчик нажатия на кнопку для воды
@bot.callback_query_handler(func=lambda call: call.data == "confirm_water")
def handle_confirmation(call):
    if call.message:
        bot.send_message(call.message.chat.id, "Ты у меня самая лучшая! 😊")
        global water_reminder_sent
        water_reminder_sent = False  # Сбросить флаг напоминания о воде


# Обработчик нажатия на кнопку для таблетки
@bot.callback_query_handler(func=lambda call: call.data == "confirm_tablet")
def handle_tablet_confirmation(call):
    if call.message:
        bot.send_message(call.message.chat.id,
                         "Просто умничка! Не забудь отметить в своём приложении, чтобы не забыть 😊")
        global tablet_reminder_sent
        tablet_reminder_sent = False  # Сбросить флаг напоминания о таблетке


# Вебхук обработчик
@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid content type', 400


# Настройка вебхука
if __name__ == "__main__":
    load_user_states()  # Загрузка состояний пользователей при старте
    port = int(os.environ.get('PORT', 8080))  # Используем порт 8080 или из окружения
    bot.remove_webhook()
    bot.set_webhook(url=f"https://vita-bot.up.railway.app/{TOKEN}")  # Ваш проект на Railway
    app.run(host='0.0.0.0', port=port)  # Запуск Flask сервера