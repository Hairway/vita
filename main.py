import telebot
import schedule
import pytz
from datetime import datetime
import time
from flask import Flask, request
import os

# Ваш токен от BotFather
TOKEN = '7598457393:AAGYDyzb67hgudu1e1wPiqet0imV-F6ZCiI'

# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

# Flask сервер для обработки вебхуков
app = Flask(__name__)

# Глобальные переменные для хранения последнего чата
last_chat_id = None
paused = False

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


# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    global last_chat_id, paused
    last_chat_id = message.chat.id
    paused = False
    bot.send_message(last_chat_id, "Котка, привет! Я тебя очень люблю ❤️\n\n"
                                   "Я стараюсь следить за тем, чтобы ты чаще пила водичку, но подумал, что могу выйти из дома, быть на тренировке или заработаться, или заучиться.\n\n"
                                   "Поэтому я специально написал этот телеграм бота, который будет напоминать тебе об этом!\n\n"
                                   "Каждый будний день с 10 до 8 вечера он каждые 2 часа будет отправлять тебе напоминание о том, что пора сделать хотя бы пару глоточков) Надо только подтвердить, что ты попила. Но не жульничай!!!\n\n"
                                   "А если ты будешь его игнорировать (а не надо), то каждые 10 минут он будет напоминать тебе)")

    # Запуск планировщика напоминаний
    start_scheduling()


# Команда /pause
@bot.message_handler(commands=['pause'])
def pause_reminders(message):
    global paused
    paused = True
    bot.send_message(message.chat.id, "Напоминания приостановлены. Используй команду /start, чтобы возобновить.")


# Функция для отправки напоминания о воде
def send_water_reminder():
    if last_chat_id and not paused:
        message = reminder_messages[datetime.now().hour % len(reminder_messages)]
        bot.send_message(last_chat_id, message)
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Выпил воду", callback_data="confirm_water")
        markup.add(confirm_button)
        bot.send_message(last_chat_id, "Не жульничай, солнышко. Нажми тогда, когда выпила водички", reply_markup=markup)


# Функция для отправки напоминания о таблетке
def send_tablet_reminder():
    if last_chat_id and not paused:
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Таблетку выпила", callback_data="confirm_tablet")
        markup.add(confirm_button)
        bot.send_message(last_chat_id, tablet_message, reply_markup=markup)


# Планировщик напоминаний
def start_scheduling():
    schedule.every().monday.at("10:00").do(send_water_reminder)
    schedule.every().monday.at("12:00").do(send_tablet_reminder)
    schedule.every().monday.at("14:00").do(send_water_reminder)
    schedule.every().monday.at("15:20").do(send_water_reminder)
    schedule.every().monday.at("16:00").do(send_water_reminder)
    schedule.every().monday.at("18:00").do(send_water_reminder)
    schedule.every().monday.at("20:00").do(send_water_reminder)

    while True:
        schedule.run_pending()
        time.sleep(60)


# Обработчик нажатия на кнопку для воды
@bot.callback_query_handler(func=lambda call: call.data == "confirm_water")
def handle_confirmation(call):
    if call.message:
        bot.send_message(call.message.chat.id, "Ты у меня самая лучшая! 😊")


# Обработчик нажатия на кнопку для таблетки
@bot.callback_query_handler(func=lambda call: call.data == "confirm_tablet")
def handle_tablet_confirmation(call):
    if call.message:
        bot.send_message(call.message.chat.id,
                         "Просто умничка! Не забудь отметить в своём приложении, чтобы не забыть 😊")


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
    port = int(os.environ.get('PORT', 8080))  # Используем порт 8080 или из окружения
    bot.remove_webhook()
    bot.set_webhook(url=f"https://vita-bot.up.railway.app/{TOKEN}")  # Укажите реальный домен
    app.run(host='0.0.0.0', port=port)  # Запуск Flask сервера