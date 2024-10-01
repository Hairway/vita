from flask import Flask, request
import telebot
import schedule
import time
from threading import Thread
import random
import json
from datetime import datetime
import pytz
import logging

# Установка уровня логирования
logging.basicConfig(level=logging.INFO)

# Ваш токен от BotFather
TOKEN = '7598457393:AAGYDyzb67hgudu1e1wPiqet0imV-F6ZCiI'

# Создаем экземпляр Flask приложения
app = Flask(__name__)
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

# Загружаем состояние пользователей
def load_user_states():
    global user_states
    try:
        with open('user_state.json', 'r') as f:
            user_states = json.load(f)
    except FileNotFoundError:
        user_states = {}

# Сохраняем состояние пользователей
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

# Обработчик нажатия на кнопку для таблетки
@bot.callback_query_handler(func=lambda call: call.data == "confirm_tablet")
def handle_tablet_confirmation(call):
    if call.message:
        bot.send_message(call.message.chat.id, "Просто умничка! Не забудь отметить в своём приложении, чтобы не забыть 😊")

# Функция для проверки времени и отправки напоминаний
def schedule_reminders():
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_time = datetime.now(moscow_tz)

    if current_time.weekday() < 5:  # 0 - понедельник, 4 - пятница
        if current_time.hour >= 10 and current_time.hour <= 20:
            send_water_reminder()
            if current_time.hour == 12:
                send_tablet_reminder()
            if current_time.hour == 16 and current_time.minute == 35:
                send_water_reminder()
        else:
            logging.info("Время не подходит для отправки напоминаний.")
    else:
        logging.info("Сегодня выходной.")

# Запускаем планировщик
def run_schedule():
    schedule.every(2).hours.at(":00").do(schedule_reminders)
    schedule.every(2).hours.at(":30").do(schedule_reminders)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Инициализация приложения перед первым запросом
@app.before_first_request
def before_first_request_func():
    load_user_states()  # Загружаем состояние пользователей при первом запросе
    # Запускаем поток для планировщика
    Thread(target=run_schedule, daemon=True).start()

# Устанавливаем вебхук
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

# Устанавливаем webhook
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url='vita-production-7c0a.up.railway.app')  # Замените на свой URL
    return "Webhook set!", 200

# Запуск Flask-приложения
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))