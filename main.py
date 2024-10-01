import telebot
import schedule
import time
from threading import Thread
from datetime import datetime
import pytz
import json

# Ваш токен от BotFather
TOKEN = '7598457393:AAGYDyzb67hgudu1e1wPiqet0imV-F6ZCiI'

# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

# Глобальная переменная для хранения последнего чата и состояния
last_chat_id = None
user_states = {}
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

# Проверка, будний ли день
def is_weekday():
    return datetime.now().weekday() < 5  # 0-4 - будние дни

# Запуск напоминаний
def start_reminders():
    while True:
        if not paused and is_weekday():
            current_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%H:%M")
            if current_time in ["10:00", "12:00", "14:00", "16:00", "18:00", "19:00", "19:05", "19:10", "20:00"]:
                send_water_reminder()
                if current_time == "12:00":
                    send_tablet_reminder()
        time.sleep(60)  # Проверяем каждую минуту

# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    global last_chat_id, paused
    last_chat_id = message.chat.id
    paused = False
    bot.send_message(last_chat_id, "Котка, привет! Я тебя очень люблю ❤️ \n\n"
                                    "Я буду напоминать тебе пить воду и принимать таблетки. Каждый будний день с 10 до 20 часов я буду отправлять тебе напоминания. "
                                    "Если ты не нажмешь кнопку подтверждения, я буду напоминать тебе каждые 10 минут, пока не нажмешь.")

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
    if last_chat_id:
        message = reminder_messages[datetime.now().hour % len(reminder_messages)]
        bot.send_message(last_chat_id, message)
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Выпил воду", callback_data="confirm_water")
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

# Запускаем бота
load_user_states()
bot.polling(none_stop=True)