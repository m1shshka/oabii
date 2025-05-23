import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__)

# Настройка Telegram-бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

try:
    bot = telebot.TeleBot(TOKEN, threaded=False)  # Отключаем потоки для вебхуков
    logger.info("Бот успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации бота: {e}")
    raise

# Создание кнопок
def create_buttons():
    logger.info("Создание кнопок")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Вопрос 1: Да", callback_data="q1_yes"))
    markup.add(InlineKeyboardButton("Вопрос 1: Нет", callback_data="q1_no"))
    markup.add(InlineKeyboardButton("Вопрос 2: Хорошо", callback_data="q2_good"))
    markup.add(InlineKeyboardButton("Вопрос 2: Плохо", callback_data="q2_bad"))
    return markup

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        logger.info(f"Получена команда /start от {message.chat.id}")
        bot.reply_to(message, "Выберите ответ на вопрос:", reply_markup=create_buttons())
        logger.info("Ответ с кнопками отправлен")
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")

# Обработка нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        logger.info(f"Получен callback: {call.data} от {call.message.chat.id}")
        answer = call.data
        if answer == "q1_yes":
            bot.answer_callback_query(call.id, "Вы выбрали: Да")
            bot.send_message(call.message.chat.id, "Спасибо за ответ на Вопрос 1: Да!")
        elif answer == "q1_no":
            bot.answer_callback_query(call.id, "Вы выбрали: Нет")
            bot.send_message(call.message.chat.id, "Спасибо за ответ на Вопрос 1: Нет!")
        elif answer == "q2_good":
            bot.answer_callback_query(call.id, "Вы выбрали: Хорошо")
            bot.send_message(call.message.chat.id, "Спасибо за ответ на Вопрос 2: Хорошо!")
        elif answer == "q2_bad":
            bot.answer_callback_query(call.id, "Вы выбрали: Плохо")
            bot.send_message(call.message.chat.id, "Спасибо за ответ на Вопрос 2: Плохо!")
        logger.info(f"Обработан callback: {answer}")
    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")

# Маршрут для вебхуков
@app.route(f"/{TOKEN}", methods=["POST"])
def get_message():
    try:
        logger.info("Получен POST-запрос от Telegram")
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        if update:
            logger.info(f"Обновление: {update}")
            # Проверяем, является ли обновление командой /start
            if update.message and update.message.text and update.message.text.startswith('/start'):
                logger.info(f"Обнаружена команда /start от {update.message.chat.id}")
                send_welcome(update.message)  # Явно вызываем обработчик
            else:
                bot.process_new_updates([update])  # Обрабатываем другие обновления
            logger.info("Обновление обработано")
        else:
            logger.warning("Получено пустое обновление")
        return "!", 200
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return "!", 500

# Главная страница для проверки
@app.route("/")
def webhook():
    try:
        logger.info("Установка вебхука")
        bot.remove_webhook()
        bot.set_webhook(url=f"https://oabii.onrender.com/{TOKEN}")
        logger.info("Вебхук установлен")
        return "Webhook set!", 200
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")
        return "Webhook error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
