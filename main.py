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

# Initialize bot and Flask with error handling
try:
    bot = telebot.TeleBot(TOKEN)
    app = Flask(__name__)
except Exception as e:
    logger.critical(f"Failed to initialize bot or Flask: {e}")
    raise


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
            # Use environment variable for state file path
            file_path = os.environ.get('STATE_FILE_PATH', '/tmp/bot_state.json')
            with open(file_path, 'w') as f:
                json.dump(state, f)
            logger.info(f"State saved successfully to {file_path}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

    def load_state(self) -> None:
        try:
            # Use environment variable for state file path
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


def reminder_thread():
    logger.info("Reminder thread started")
    last_day = -1

    while True:
        try:
            current_time = datetime.now(pytz.timezone('Europe/Moscow'))

            # Reset state at the start of a new day
            if current_time.day != last_day:
                reset_daily_state()
                last_day = current_time.day

            if is_weekday():
                hour = current_time.hour
                minute = current_time.minute

                # Send reminders with error handling for each user
                if hour in [10, 12, 14, 16, 18, 20] and minute == 0:
                    logger.info(f"Sending scheduled reminders for hour {hour}")
                    for chat_id in state.chat_ids:
                        try:
                            send_water_reminder(chat_id, hour)
                            if hour == 12:
                                send_tablet_reminder(chat_id)
                        except Exception as e:
                            logger.error(f"Error sending reminders to {chat_id}: {e}")
                            continue

            # Sleep with error handling
            try:
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in sleep: {e}")
                time.sleep(5)  # Shorter sleep on error

        except Exception as e:
            logger.error(f"Error in reminder thread: {e}")
            time.sleep(5)  # Shorter sleep on error


# Webhook route with better error handling
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


# Main execution with proper error handling
if __name__ == "__main__":
    try:
        # Load state
        state.load_state()

        # Start reminder thread
        reminder_thread = Thread(target=reminder_thread)
        reminder_thread.daemon = True  # Changed to True for proper cleanup
        reminder_thread.start()

        # Set up webhook with validation
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