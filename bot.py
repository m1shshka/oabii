import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import os

# Инициализация Flask для вебхуков
app = Flask(__name__)

# Настройка Telegram-бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Токен будет загружен из переменной окружения
bot = telebot.TeleBot(TOKEN)

# Создание кнопок
def create_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Вопрос 1: Да", callback_data="q1_yes"))
    markup.add(InlineKeyboardButton("Вопрос 1: Нет", callback_data="q1_no"))
    markup.add(InlineKeyboardButton("Вопрос 2: Хорошо", callback_data="q2_good"))
    markup.add(InlineKeyboardButton("Вопрос 2: Плохо", callback_data="q2_bad"))
    return markup

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Выберите ответ на вопрос:", reply_markup=create_buttons())

# Обработка нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
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

# Маршрут для вебхуков
@app.route(f"/{TOKEN}", methods=["POST"])
def get_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

# Главная страница для проверки
@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"https://my-telegram-bot-123.onrender.com/{TOKEN}")
    return "Webhook set!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
