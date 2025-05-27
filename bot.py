import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import os
import logging
import json
import re
import requests
import pymorphy3

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__)

# Настройка Telegram-бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не найден")
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

try:
    bot = telebot.TeleBot(TOKEN, threaded=False)
    logger.info("Бот успешно инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации бота: {e}")
    raise

# Загрузка FAQ
try:
    with open('faq.json', 'r', encoding='utf-8') as f:
        faq_data = json.load(f)
    logger.info("FAQ успешно загружен")
except Exception as e:
    logger.error(f"Ошибка загрузки faq.json: {e}")
    raise

# Инициализация pymorphy3 для морфологического анализа
morph = pymorphy3.MorphAnalyzer()

# URL Apps Script
APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbyNhhsqtMavUkSN0SvgmiZZMKsWkorAidfrQ5bulQB0KtA3iM8zBp7-Es8TdQOGe9Dkww/exec'

# Создание кнопок для категорий
def create_category_buttons():
    markup = InlineKeyboardMarkup()
    for i, category in enumerate(faq_data['categories']):
        markup.add(InlineKeyboardButton(category['name'], callback_data=f"cat_{i}"))
    markup.add(InlineKeyboardButton("Поиск по ключевому слову 🔍", callback_data="search"))
    logger.info(f"Созданы кнопки категорий: {[cat['name'] for cat in faq_data['categories']]}")
    return markup

# Создание кнопок для подкатегорий
def create_subcategory_buttons(cat_index):
    markup = InlineKeyboardMarkup()
    try:
        category = faq_data['categories'][cat_index]
        for i, subcategory in enumerate(category['subcategories']):
            markup.add(InlineKeyboardButton(subcategory['name'], callback_data=f"subcat_{cat_index}_{i}"))
        if category['name'] == "Абитуриенту":
            markup.add(InlineKeyboardButton("Оставить заявку 📋", callback_data="apply"))
        markup.add(InlineKeyboardButton("Назад ⬅️", callback_data="back_to_categories"))
        logger.info(f"Созданы кнопки подкатегорий для {category['name']}")
    except IndexError:
        logger.error(f"Неверный индекс категории: {cat_index}")
    return markup

# Создание кнопок для вопросов
def create_question_buttons(cat_index, subcat_index):
    markup = InlineKeyboardMarkup()
    try:
        subcategory = faq_data['categories'][cat_index]['subcategories'][subcat_index]
        for i, question in enumerate(subcategory['questions'][:5], 1):
            markup.add(InlineKeyboardButton(f"Вопрос {i} ❓", callback_data=f"q_{question['id']}"))
        markup.add(InlineKeyboardButton("Назад ⬅️", callback_data=f"back_to_subcat_{cat_index}"))
        logger.info(f"Созданы кнопки вопросов для {subcategory['name']}")
    except IndexError:
        logger.error(f"Неверный индекс: cat_index={cat_index}, subcat_index={subcat_index}")
    return markup

# Форматирование текста вопросов
def get_questions_text(cat_index, subcat_index):
    try:
        subcategory = faq_data['categories'][cat_index]['subcategories'][subcat_index]
        text = f"📚 *{subcategory['name']}*\n\n"
        for i, question in enumerate(subcategory['questions'][:5], 1):
            text += f"_{i}\\. {question['question']}_\n"
        text += "\nВыберите номер вопроса или вернитесь назад\\."
        return text
    except IndexError:
        logger.error(f"Неверный индекс: cat_index={cat_index}, subcat_index={subcat_index}")
        return "❌ Ошибка: категория не найдена."

# Поиск вопросов с учетом склонений
def search_questions(keyword):
    results = []
    normalized_keyword = morph.parse(keyword)[0].normal_form  # Приведение к начальной форме
    for category in faq_data['categories']:
        for subcategory in category['subcategories']:
            for question in subcategory['questions']:
                question_words = question['question'].split()
                answer_words = question['answer'].split()
                for word in question_words + answer_words:
                    normalized_word = morph.parse(word)[0].normal_form
                    if normalized_keyword in normalized_word:
                        results.append(question)
                        break
    return results[:5]

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        logger.info(f"Получена команда /start от {message.chat.id}")
        bot.reply_to(
            message,
            "👋 *Добро пожаловать, Михаил!* Я консультант по вопросам обучения\\. Выберите категорию:",
            reply_markup=create_category_buttons(),
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")

# Обработка команды /test
@bot.message_handler(commands=['test'])
def send_test(message):
    try:
        logger.info(f"Получена команда /test от {message.chat.id}")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Вопрос 1: Да ✅", callback_data="q1_yes"))
        markup.add(InlineKeyboardButton("Вопрос 1: Нет ❌", callback_data="q1_no"))
        markup.add(InlineKeyboardButton("Вопрос 2: Хорошо 👍", callback_data="q2_good"))
        markup.add(InlineKeyboardButton("Вопрос 2: Плохо 👎", callback_data="q2_bad"))
        bot.reply_to(
            message,
            "🧪 *Выберите ответ на тестовый вопрос:*",
            reply_markup=markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке /test: {e}")

# Обработка команды /search
@bot.message_handler(commands=['search'])
def start_search(message):
    try:
        logger.info(f"Получена команда /search от {message.chat.id}")
        bot.reply_to(message, "🔍 Введите ключевое слово для поиска:")
        bot.register_next_step_handler(message, process_search)
    except Exception as e:
        logger.error(f"Ошибка при обработке /search: {e}")

# Обработка поиска
def process_search(message):
    try:
        keyword = message.text.strip()
        logger.info(f"Поиск по ключевому слову: {keyword} от {message.chat.id}")
        results = search_questions(keyword)
        if results:
            text = f"🔍 *Результаты поиска по '{keyword}':*\n\n"
            markup = InlineKeyboardMarkup()
            for i, result in enumerate(results, 1):
                text += f"_{i}\\. {result['question']}_\n"
                markup.add(InlineKeyboardButton(f"Вопрос {i} ❓", callback_data=f"q_{result['id']}"))
            markup.add(InlineKeyboardButton("Назад ⬅️", callback_data="back_to_categories"))
            bot.reply_to(message, text, reply_markup=markup, parse_mode='MarkdownV2')
        else:
            bot.reply_to(
                message,
                f"😕 По запросу *{keyword}* ничего не найдено\\.",
                reply_markup=create_category_buttons(),
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        bot.reply_to(message, "❌ Произошла ошибка.", reply_markup=create_category_buttons())

# Обработка заявок
def start_application(message):
    try:
        user_data = {"telegramId": str(message.chat.id)}
        logger.info(f"Начало заявки для {message.chat.id}: {user_data}")
        bot.reply_to(message, "📝 Введите ФИО (например, Носиков Михаил Валерьевич):")
        bot.register_next_step_handler(message, process_name, user_data)
    except Exception as e:
        logger.error(f"Ошибка при оформлении заявки: {e}")

def process_name(message, user_data):
    try:
        user_data["fio"] = message.text.strip()
        logger.info(f"ФИО: {user_data['fio']} для {message.chat.id}")
        bot.reply_to(message, "📞 Введите номер телефона (например, +79511121899):")
        bot.register_next_step_handler(message, process_phone, user_data)
    except Exception as e:
        logger.error(f"Ошибка при обработке ФИО: {e}")

def process_phone(message, user_data):
    try:
        user_data["phone"] = message.text.strip()
        logger.info(f"Телефон: {user_data['phone']} для {message.chat.id}")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Высшее образование 🎓", callback_data=f"prog_vo_{message.chat.id}"))
        markup.add(InlineKeyboardButton("Среднее профессиональное 🛠️", callback_data=f"prog_spo_{message.chat.id}"))
        bot.reply_to(
            message,
            "🎓 *Выберите программу обучения:*",
            reply_markup=markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке телефона: {e}")

# Обработка callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        logger.info(f"Получен callback: {call.data} от {call.message.chat.id}")
        data = call.data

        # Тестовые кнопки
        if data in ["q1_yes", "q1_no", "q2_good", "q2_bad"]:
            answers = {"q1_yes": "Да ✅", "q1_no": "Нет ❌", "q2_good": "Хорошо 👍", "q2_bad": "Плохо 👎"}
            bot.answer_callback_query(call.id, f"Вы выбрали: {answers[data]}")
            bot.send_message(
                call.message.chat.id,
                f"✅ *Спасибо за ответ:* {answers[data]}",
                parse_mode='MarkdownV2'
            )
            return

        # Категории
        if data.startswith("cat_"):
            cat_index = int(data[4:])
            bot.answer_callback_query(call.id)
            category_name = faq_data['categories'][cat_index]['name']
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"📚 *Выберите подкатегорию в '{category_name}':*",
                reply_markup=create_subcategory_buttons(cat_index),
                parse_mode='MarkdownV2'
            )
            return

        # Подкатегории
        if data.startswith("subcat_"):
            cat_index, subcat_index = map(int, data[7:].split("_"))
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=get_questions_text(cat_index, subcat_index),
                reply_markup=create_question_buttons(cat_index, subcat_index),
                parse_mode='MarkdownV2'
            )
            return

        # Вопросы
        if data.startswith("q_"):
            question_id = int(data[2:])
            for category in faq_data['categories']:
                for subcategory in category['subcategories']:
                    for question in subcategory['questions']:
                        if question['id'] == question_id:
                            bot.answer_callback_query(call.id)
                            bot.send_message(
                                call.message.chat.id,
                                f"❓ *Вопрос:* {question['question']}\n\n✅ *Ответ:* {question['answer']}",
                                reply_markup=create_category_buttons(),
                                parse_mode='MarkdownV2'
                            )
                            return

        # Заявка
        if data == "apply":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "📝 *Начнем оформление заявки:*",
                parse_mode='MarkdownV2'
            )
            start_application(call.message)
            return

        # Программа обучения
        if data.startswith("prog_"):
            parts = data.split("_")
            program = "Высшее образование" if parts[1] == "vo" else "Среднее профессиональное"
            chat_id = int(parts[2])
            user_data = {
                "telegramId": str(chat_id),
                "fio": call.message.text if hasattr(call.message, 'text') else "",
                "phone": "",
                "program": program
            }
            # Попробуем восстановить user_data из предыдущих сообщений
            if hasattr(call.message, 'reply_to_message'):
                user_data["phone"] = call.message.reply_to_message.text if call.message.reply_to_message else ""
                if hasattr(call.message.reply_to_message, 'reply_to_message'):
                    user_data["fio"] = call.message.reply_to_message.reply_to_message.text if call.message.reply_to_message.reply_to_message else ""
            logger.info(f"Отправка заявки: {user_data}")
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "✅ *Заявка отправлена\\!* Мы свяжемся с вами\\.",
                reply_markup=create_category_buttons(),
                parse_mode='MarkdownV2'
            )
            # Отправка в Apps Script
            response = requests.post(APPS_SCRIPT_URL, json=user_data)
            if response.json().get('status') == 'success':
                logger.info(f"Заявка сохранена: {user_data}")
            else:
                logger.error(f"Ошибка сохранения заявки: {response.json()}")
            return

        # Возврат
        if data == "back_to_categories":
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="📚 *Выберите категорию:*",
                reply_markup=create_category_buttons(),
                parse_mode='MarkdownV2'
            )
            return

        if data.startswith("back_to_subcat_"):
            cat_index = int(data[15:])
            category_name = faq_data['categories'][cat_index]['name']
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"📚 *Выберите подкатегорию в '{category_name}':*",
                reply_markup=create_subcategory_buttons(cat_index),
                parse_mode='MarkdownV2'
            )
            return

        # Поиск
        if data == "search":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "🔍 *Введите ключевое слово для поиска:*",
                parse_mode='MarkdownV2'
            )
            bot.register_next_step_handler(call.message, process_search)
            return

    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")

# Маршрут для вебхуков
@app.route(f"/{TOKEN}", methods=['POST'])
def get_message():
    try:
        logger.info("Получен POST-запрос от Telegram")
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        if update:
            bot.process_new_updates([update])
        return "!", 200
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return "!", 500

# Главная страница
@app.route("/")
def webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"https://oabii.onrender.com/{TOKEN}")
        return "Webhook set!", 200
    except Exception as e:
        logger.error(f"Ошибка при установке вебхука: {e}")
        return "Webhook error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
