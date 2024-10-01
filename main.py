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

# Глобальная переменная для хранения последнего чата и состояния теста
last_chat_id = None
test_mode = False
user_states = {}

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

# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    global last_chat_id
    last_chat_id = message.chat.id
    bot.send_message(last_chat_id, "Котка, привет! Я тебя очень люблю ❤️ \n\n"
                                    "Я стараюсь следить за тем, чтобы ты чаще пила водичку, но подумал, что могу выйти из дома, быть на тренировке или заработаться, или заучиться.\n\n"
                                    "Поэтому я специально написал этот телеграм бота, который будет напоминать тебе об этом 😁\n\n"
                                    "Каждый будний день с 10 до 8 вечера он каждые 2 часа будет отправлять тебе напоминание о том, что пора сделать хотя бы пару глоточков) Надо только подтвердить, что ты попила. Но не жульничай!\n\n"
                                    "А если ты будешь его игнорировать (а не надо), то каждые 10 минут он будет напоминать тебе вновь)))")

# Команда /test
@bot.message_handler(commands=['test'])
def test_mode_start(message):
    global test_mode
    test_mode = True
    bot.send_message(message.chat.id, "Тестовый режим активирован! Сейчас отправлю напоминания...")
    send_water_reminder()
    send_tablet_reminder()

# Команда /testend
@bot.message_handler(commands=['testend'])
def test_mode_end(message):
    global test_mode
    test_mode = False
    bot.send_message(message.chat.id, "Тестовый режим завершен. Бот вернулся к обычному режиму.")

# Функция для отправки напоминания о воде
def send_water_reminder():
    if last_chat_id:
        # Выбираем случайное сообщение
        message = reminder_messages[datetime.now().hour % len(reminder_messages)]
        bot.send_message(last_chat_id, message)
        # Добавляем inline кнопку для подтверждения
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Выпил воду", callback_data="confirm_water")
        markup.add(confirm_button)
        bot.send_message(last_chat_id, "Не жульничай, солнышко. Нажми тогда, когда выпила водички", reply_markup=markup)

        # Если в тестовом режиме, повторяем через минуту
        if test_mode:
            bot.send_message(last_chat_id, "Если не подтвердил, я напомню через минуту.")
            Thread(target=repeat_water_reminder, args=(last_chat_id,)).start()

# Функция для повторного напоминания о воде
def repeat_water_reminder(chat_id):
    time.sleep(60)  # Ждем минуту
    if test_mode:  # Проверяем, всё еще в тестовом режиме
        send_water_reminder()

# Функция для отправки напоминания о таблетке
def send_tablet_reminder():
    if last_chat_id:
        markup = telebot.types.InlineKeyboardMarkup()
        confirm_button = telebot.types.InlineKeyboardButton("✅ Таблетку выпила", callback_data="confirm_tablet")
        markup.add(confirm_button)
        bot.send_message(last_chat_id, tablet_message, reply_markup=markup)

        # Если в тестовом режиме, повторяем через минуту
        if test_mode:
            bot.send_message(last_chat_id, "Если не подтвердил, я напомню через минуту.")
            Thread(target=repeat_tablet_reminder, args=(last_chat_id,)).start()

# Функция для повторного напоминания о таблетке
def repeat_tablet_reminder(chat_id):
    time.sleep(60)  # Ждем минуту
    if test_mode:  # Проверяем, всё еще в тестовом режиме
        send_tablet_reminder()

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