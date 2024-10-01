import telebot
import schedule
import time
from threading import Thread
import json
import random
from datetime import datetime
import logging
import pytz  # Импортируем pytz для работы с часовыми поясами

# Установка уровня логирования
logging.basicConfig(level=logging.INFO)

# Ваш токен от BotFather
TOKEN = '7598457393:AAGYDyzb67hgudu1e1wPiqet0imV-F6ZCiI'

# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

# Глобальные переменные
last_chat_id = None
user_states = {}
reminder_messages = [
    "Котка, пора сделать пару глоточков воды! 💧",
    "Проверь, полный ли у тебя стакан. Если нет, то попроси меня, если я дома. Я принесу и надо будет попить💧",
    "Любочка, водичка стоит возле тебя и надо попить!💧",
    "Время оторваться от работы, немного выдохнуть и попить воды! 💧",
    "Если сейчас попить воды, то твой любимый котка станет счастливее! 💧",
    "Кота, не жульничай! Сделай глоточек и нажми на кнопку💧"
]
tablet_message = "А ещё, котка, уже время выпить таблетку! Попроси меня и я принесу 💊"
last_reminder_message = None

# Функция для загрузки состояния пользователей
def load_user_states():
    global user_states
    try:
        with open('user_state.json', 'r') as f:
            user_states = json.load(f)
    except FileNotFoundError:
        user_states = {}

# Функция для сохранения состояния пользователей
def save_user_states():
    with open('user_state.json', 'w') as f:
        json.dump(user_states, f)

# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    global last_chat_id
    last_chat_id = message.chat.id
    bot.send_message(last_chat_id, "Котка, привет! Я тебя очень люблю ❤️ \n\n"
                                    "Я стараюсь следить за тем, чтобы ты чаще пила водичку, но подумал, что могу выйти из дома, быть на тренировке или заработаться, или заучиться.\n\n"
                                    "Поэтому я специально написал этот телеграм бота, который будет напоминать тебе об этом 😁\n\n"
                                    "Каждый будний день с 10 до 8 вечера он каждые 2 часа будет отправлять тебе напоминание о том, что пора сделать хотя бы пару глоточков) Надо только подтвердить, что ты попила. Но не жульничай!\n\n"
                                    "А если ты будешь игнорировать (а не надо), то каждые 10 минут он будет напоминать тебе вновь)))")

# Функция для отправки напоминания о воде
def send_water_reminder():
    global last_reminder_message
    if last_chat_id:
        message = random.choice([msg for msg in reminder_messages if msg != last_reminder_message])
        last_reminder_message = message
        bot.send_message(last_chat_id, message)

        # Добавляем inline кнопку для подтверждения
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Выпила воду", callback_data="confirm_water")
        markup.add(confirm_button)
        bot.send_message(last_chat_id, "Не жульничай, солнышко. Нажми тогда, когда выпила водички", reply_markup=markup)

# Функция для отправки напоминания о таблетке
def send_tablet_reminder():
    if last_chat_id:
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Таблетку выпила", callback_data="confirm_tablet")
        markup.add(confirm_button)
        bot.send_message(last_chat_id, tablet_message, reply_markup=markup)

# Обработчик нажатия на кнопку для воды
@bot.callback_query_handler(func=lambda call: call.data == "confirm_water")
def handle_confirmation(call):
    if call.message:
        bot.send_message(call.message.chat.id, "Ты у меня самая лучшая! 😊")
        # Здесь можно добавить логику для сохранения состояния

# Обработчик нажатия на кнопку для таблетки
@bot.callback_query_handler(func=lambda call: call.data == "confirm_tablet")
def handle_tablet_confirmation(call):
    if call.message:
        bot.send_message(call.message.chat.id, "Просто умничка! Не забудь отметить в своём приложении, чтобы не забыть 😊")
        # Здесь можно добавить логику для сохранения состояния

# Функция для проверки времени и отправки напоминаний
def schedule_reminders():
    # Устанавливаем московское время
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_time = datetime.now(moscow_tz)

    # Проверяем, что сегодня будний день
    if current_time.weekday() < 5:  # 0 - понедельник, 4 - пятница
        if current_time.hour >= 10 and current_time.hour <= 20:
            send_water_reminder()
            # Отправляем напоминание о таблетке, если это 12:00
            if current_time.hour == 12:
                send_tablet_reminder()
            # Отправляем напоминание о воде, если это 16:31
            if current_time.hour == 16 and current_time.minute == 31:
                send_water_reminder()
        else:
            logging.info("Время не подходит для отправки напоминаний.")
    else:
        logging.info("Сегодня выходной.")

# Запускаем планировщик
def run_schedule():
    schedule.every(2).hours.at(":00").do(schedule_reminders)  # Каждые 2 часа
    schedule.every(2).hours.at(":30").do(schedule_reminders)  # Каждые 2 часа
    while True:
        schedule.run_pending()  # Запускаем все запланированные задачи
        time.sleep(60)  # Ждем 1 минуту

# Запускаем поток для планировщика
Thread(target=run_schedule, daemon=True).start()  # Убедитесь, что поток является демоном

# Загружаем состояние пользователей и запускаем бота
load_user_states()
bot.polling(none_stop=True)  # Бот работает в бесконечном цикле