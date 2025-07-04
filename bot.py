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

# Инициализация pymorphy3
morph = pymorphy3.MorphAnalyzer()

# URL Apps Script
APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbyNhhsqtMavUkSN0SvgmiZZMKsWkorAidfrQ5bulQB0KtA3iM8zBp7-Es8TdQOGe9Dkww/exec'

# Хранение данных заявок
user_data_storage = {}

# Экранирование специальных символов для MarkdownV2
def escape_markdown(text):
    special_chars = r'[_*[\]()~`>#+-=|{}.!]'
    return re.sub(special_chars, r'\\\g<0>', str(text))

# Создание кнопок для категорий
def create_category_buttons():
    markup = InlineKeyboardMarkup()
    for i, category in enumerate(faq_data['categories']):
        markup.add(InlineKeyboardButton(f"📚 {category['name']}", callback_data=f"cat_{i}"))
    markup.add(InlineKeyboardButton("🔍 Поиск по ключевому слову", callback_data="search"))
    logger.info(f"Созданы кнопки категорий: {[cat['name'] for cat in faq_data['categories']]}")
    return markup

# Создание кнопок для подкатегорий
def create_subcategory_buttons(cat_index):
    markup = InlineKeyboardMarkup()
    try:
        category = faq_data['categories'][cat_index]
        for i, subcategory in enumerate(category['subcategories']):
            markup.add(InlineKeyboardButton(f"📌 {subcategory['name']}", callback_data=f"subcat_{cat_index}_{i}"))
        if category['name'] == "Абитуриенту":
            markup.add(InlineKeyboardButton("📋 Оставить заявку", callback_data="apply"))
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_categories"))
        logger.info(f"Созданы кнопки подкатегорий для {category['name']}")
    except IndexError:
        logger.error(f"Неверный индекс категории: {cat_index}")
    return markup

# Создание кнопок вопросов
def create_question_buttons(cat_index, subcat_index):
    markup = InlineKeyboardMarkup()
    try:
        subcategory = faq_data['categories'][cat_index]['subcategories'][subcat_index]
        for i, question in enumerate(subcategory['questions'][:5], 1):
            markup.add(InlineKeyboardButton(f"❓ Вопрос {i}", callback_data=f"q_{question['id']}"))
        markup.add(InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_subcat_{cat_index}"))
        logger.info(f"Созданы кнопки вопросов для {subcategory['name']}")
    except IndexError:
        logger.error(f"Неверный индекс: cat_index={cat_index}, subcat_index={subcat_index}")
    return markup

# Форматирование текста вопросов
def get_questions_text(cat_index, subcat_index):
    try:
        subcategory = faq_data['categories'][cat_index]['subcategories'][subcat_index]
        text = f"✨ *{escape_markdown(subcategory['name'])}*\n\n"
        for i, question in enumerate(subcategory['questions'][:5], 1):
            text += f"_{i}\\. {escape_markdown(question['question'])} ❓_\n"
        text += "\nВыберите номер вопроса или вернитесь назад\\."
        return text
    except IndexError:
        logger.error(f"Неверный индекс: cat_index={cat_index}, subcat_index={subcat_index}")
        return "❌ Ошибка: категория не найдена."

# Поиск вопросов
def search_questions(keyword):
    results = []
    normalized_keyword = morph.parse(keyword)[0].normal_form
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

# Обработка /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        logger.info(f"Получена команда /start от {message.chat.id}")
        user_name = message.from_user.first_name or message.from_user.username or "Курсант"
        if user_name.startswith('@'):
            user_name = user_name[1:]  # Убираем @ для красоты
        bot.reply_to(
            message,
            escape_markdown(f"Здравия желаю, {user_name}! 👋 Я Ассистент курсанта по вопросам обучения. Выбери категорию:"),
            reply_markup=create_category_buttons(),
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")

# Обработка /test
@bot.message_handler(commands=['test'])
def send_test(message):
    try:
        logger.info(f"Получена команда /test от {message.chat.id}")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Вопрос 1: Да", callback_data="q1_yes"))
        markup.add(InlineKeyboardButton("❌ Вопрос 1: Нет", callback_data="q1_no"))
        markup.add(InlineKeyboardButton("👍 Вопрос 2: Хорошо", callback_data="q2_good"))
        markup.add(InlineKeyboardButton("👎 Вопрос 2: Плохо", callback_data="q2_bad"))
        bot.reply_to(
            message,
            escape_markdown("🧪 Выбери ответ на тестовый вопрос:"),
            reply_markup=markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке /test: {e}")

# Обработка /search
@bot.message_handler(commands=['search'])
def start_search(message):
    try:
        logger.info(f"Получена команда /search от {message.chat.id}")
        bot.reply_to(message, escape_markdown("🔍 Введи ключевое слово для поиска:"), parse_mode='MarkdownV2')
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
            text = f"🔍 *Результаты поиска по '{escape_markdown(keyword)}':*\n\n"
            markup = InlineKeyboardMarkup()
            for i, result in enumerate(results, 1):
                text += f"_{i}\\. {escape_markdown(result['question'])} ❓_\n"
                markup.add(InlineKeyboardButton(f"❓ Вопрос {i}", callback_data=f"q_{result['id']}"))
            markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_categories"))
            bot.reply_to(message, text, reply_markup=markup, parse_mode='MarkdownV2')
        else:
            bot.reply_to(
                message,
                escape_markdown(f"😕 Не могу знать, в моей базе знаний отсутствует информация по запросу *{keyword}*."),
                reply_markup=create_category_buttons(),
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        bot.reply_to(message, escape_markdown("❌ Произошла ошибка."), reply_markup=create_category_buttons(), parse_mode='MarkdownV2')

# Обработка заявок
def start_application(call):
    try:
        chat_id = str(call.message.chat.id)
        username = call.from_user.username
        logger.info(f"Начало заявки для chat_id: {chat_id}, username: {username}")
        if not username:
            bot.send_message(
                chat_id,
                escape_markdown("⚠️ У вас не указан username в Telegram (например, @mishanosikov). Пожалуйста, установите его в настройках Telegram и попробуйте снова, или укажите username вручную:"),
                parse_mode='MarkdownV2'
            )
            bot.register_next_step_handler(call.message, process_manual_username, chat_id)
            return
        user_data_storage[chat_id] = {"telegramId": f"@{username}", "chatId": chat_id}
        logger.info(f"Заявка инициализирована: {user_data_storage[chat_id]}")
        bot.send_message(
            chat_id,
            escape_markdown("📝 Введи ФИО (например, Носиков Михаил Валерьевич):"),
            parse_mode='MarkdownV2'
        )
        bot.register_next_step_handler(call.message, process_name, chat_id)
    except Exception as e:
        logger.error(f"Ошибка при оформлении заявки для {chat_id}: {e}")
        bot.send_message(chat_id, escape_markdown("❌ Произошла ошибка."), reply_markup=create_category_buttons(), parse_mode='MarkdownV2')

def process_manual_username(message, chat_id):
    try:
        username = message.text.strip()
        if not username.startswith('@'):
            username = f"@{username}"
        user_data_storage[chat_id] = {"telegramId": username, "chatId": chat_id}
        logger.info(f"Ручной username: {username} для {chat_id}")
        bot.reply_to(
            message,
            escape_markdown("📝 Введи ФИО (например, Носиков Михаил Валерьевич):"),
            parse_mode='MarkdownV2'
        )
        bot.register_next_step_handler(message, process_name, chat_id)
    except Exception as e:
        logger.error(f"Ошибка при обработке ручного username для {chat_id}: {e}")
        bot.reply_to(message, escape_markdown("❌ Произошла ошибка."), reply_markup=create_category_buttons(), parse_mode='MarkdownV2')

def process_name(message, chat_id):
    try:
        user_data_storage[chat_id]["fio"] = message.text.strip()
        logger.info(f"ФИО: {user_data_storage[chat_id]['fio']} для {chat_id}")
        bot.reply_to(
            message,
            escape_markdown("📞 Введи номер телефона (например, +79511222890):"),
            parse_mode='MarkdownV2'
        )
        bot.register_next_step_handler(message, process_phone, chat_id)
    except Exception as e:
        logger.error(f"Ошибка при обработке ФИО для {chat_id}: {e}")
        bot.reply_to(message, escape_markdown("❌ Произошла ошибка."), reply_markup=create_category_buttons(), parse_mode='MarkdownV2')

def process_phone(message, chat_id):
    try:
        phone = message.text.strip()
        # Валидация номера телефона
        phone = re.sub(r'\D', '', phone)  # Удаляем нецифровые символы
        if not phone.startswith('7') and not phone.startswith('8'):
            bot.reply_to(
                message,
                escape_markdown("❌ Номер телефона должен начинаться с +7, 7 или 8. Попробуй снова:"),
                parse_mode='MarkdownV2'
            )
            bot.register_next_step_handler(message, process_phone, chat_id)
            return
        if phone.startswith('8'):
            phone = '7' + phone[1:]
        if not phone.startswith('+'):
            phone = '+' + phone
        user_data_storage[chat_id]["phone"] = phone
        logger.info(f"Телефон: {user_data_storage[chat_id]['phone']} для {chat_id}")
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎓 Высшее образование", callback_data=f"prog_vo_{chat_id}"))
        markup.add(InlineKeyboardButton("🛠️ Среднее профессиональное", callback_data=f"prog_spo_{chat_id}"))
        bot.reply_to(
            message,
            escape_markdown("🎓 Выбери программу обучения:"),
            reply_markup=markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке телефона для {chat_id}: {e}")
        bot.reply_to(message, escape_markdown("❌ Произошла ошибка."), reply_markup=create_category_buttons(), parse_mode='MarkdownV2')

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
                escape_markdown(f"✅ Спасибо за ответ: {answers[data]}"),
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
                text=escape_markdown(f"✨ Выбери подкатегорию в '{category_name}':"),
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
                                escape_markdown(f"❓ Вопрос: {question['question']}\n\n✅ Ответ: {question['answer']}"),
                                reply_markup=create_category_buttons(),
                                parse_mode='MarkdownV2'
                            )
                            return

        # Заявка
        if data == "apply":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                escape_markdown("📝 Начнем оформление заявки:"),
                parse_mode='MarkdownV2'
            )
            start_application(call)
            return

        # Программа обучения
        if data.startswith("prog_"):
            parts = data.split("_")
            program = "Высшее образование" if parts[1] == "vo" else "Среднее профессиональное"
            chat_id = parts[2]
            if chat_id in user_data_storage:
                user_data = user_data_storage[chat_id]
                user_data["program"] = program
                logger.info(f"Отправка заявки: {user_data}")
                bot.answer_callback_query(call.id)
                bot.send_message(
                    call.message.chat.id,
                    escape_markdown("✅ Заявка отправлена! Мы свяжемся с вами. 📞"),
                    reply_markup=create_category_buttons(),
                    parse_mode='MarkdownV2'
                )
                # Отправка в Apps Script
                response = requests.post(APPS_SCRIPT_URL, json=user_data)
                if response.json().get('status') == 'success':
                    logger.info(f"Заявка сохранена: {user_data}")
                else:
                    logger.error(f"Ошибка сохранения заявки: {response.json()}")
                del user_data_storage[chat_id]
            else:
                logger.error(f"Данные заявки не найдены для {chat_id}")
                bot.send_message(
                    call.message.chat.id,
                    escape_markdown("❌ Ошибка: данные заявки потеряны. Попробуй снова."),
                    reply_markup=create_category_buttons(),
                    parse_mode='MarkdownV2'
                )
            return

        # Возврат
        if data == "back_to_categories":
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=escape_markdown("📚 Выбери категорию:"),
                reply_markup=create_category_buttons(),
                parse_mode='MarkdownV2'
            )
            return

        if data.startswith("back_to_subcat_"):
            cat_index = int(data[15:])
            category_name = faq_data['categories'][cat_index]['name']
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=escape_markdown(f"✨ Выбери подкатегорию в '{category_name}':"),
                reply_markup=create_subcategory_buttons(cat_index),
                parse_mode='MarkdownV2'
            )
            return

        # Поиск
        if data == "search":
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                escape_markdown("🔍 Введи ключевое слово для поиска:"),
                parse_mode='MarkdownV2'
            )
            bot.register_next_step_handler(call.message, process_search)
            return

    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        bot.answer_callback_query(call.id, escape_markdown("❌ Произошла ошибка."))

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
