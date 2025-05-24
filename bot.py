import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import os
import logging
import json
import re

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

# Загрузка FAQ из JSON
try:
    with open('faq.json', 'r', encoding='utf-8') as f:
        faq_data = json.load(f)
    logger.info("FAQ успешно загружен")
except Exception as e:
    logger.error(f"Ошибка загрузки faq.json: {e}")
    raise

# Создание кнопок для тестовых вопросов (старая функциональность)
def create_test_buttons():
    logger.info("Создание тестовых кнопок")
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Вопрос 1: Да", callback_data="q1_yes"))
    markup.add(InlineKeyboardButton("Вопрос 1: Нет", callback_data="q1_no"))
    markup.add(InlineKeyboardButton("Вопрос 2: Хорошо", callback_data="q2_good"))
    markup.add(InlineKeyboardButton("Вопрос 2: Плохо", callback_data="q2_bad"))
    return markup

# Создание кнопок для категорий
def create_category_buttons():
    markup = InlineKeyboardMarkup()
    for i, category in enumerate(faq_data['categories']):
        markup.add(InlineKeyboardButton(category['name'], callback_data=f"cat_{i}"))
    markup.add(InlineKeyboardButton("Поиск по ключевому слову", callback_data="search"))
    logger.info(f"Созданы кнопки категорий: {[cat['name'] for cat in faq_data['categories']]}")
    return markup

# Создание кнопок для подкатегорий
def create_subcategory_buttons(cat_index):
    markup = InlineKeyboardMarkup()
    try:
        category = faq_data['categories'][cat_index]
        for i, subcategory in enumerate(category['subcategories']):
            markup.add(InlineKeyboardButton(subcategory['name'], callback_data=f"subcat_{cat_index}_{i}"))
        markup.add(InlineKeyboardButton("Назад", callback_data="back_to_categories"))
        logger.info(f"Созданы кнопки подкатегорий для категории {category['name']}: {[sub['name'] for sub in category['subcategories']]}")
    except IndexError:
        logger.error(f"Неверный индекс категории: {cat_index}")
        markup.add(InlineKeyboardButton("Назад", callback_data="back_to_categories"))
    return markup

# Создание кнопок для вопросов
def create_question_buttons(cat_index, subcat_index):
    markup = InlineKeyboardMarkup()
    try:
        subcategory = faq_data['categories'][cat_index]['subcategories'][subcat_index]
        for i, question in enumerate(subcategory['questions'][:5], 1):
            markup.add(InlineKeyboardButton(f"Вопрос {i}", callback_data=f"q_{question['id']}"))
        markup.add(InlineKeyboardButton("Назад", callback_data=f"back_to_subcat_{cat_index}"))
        logger.info(f"Созданы кнопки вопросов для подкатегории {subcategory['name']}: {[q['question'][:30] + '...' for q in subcategory['questions'][:5]]}")
    except IndexError:
        logger.error(f"Неверный индекс: cat_index={cat_index}, subcat_index={subcat_index}")
        markup.add(InlineKeyboardButton("Назад", callback_data=f"back_to_subcat_{cat_index}"))
    return markup

# Получение текста вопросов для подкатегории
def get_questions_text(cat_index, subcat_index):
    try:
        subcategory = faq_data['categories'][cat_index]['subcategories'][subcat_index]
        text = f"Вопросы в категории '{subcategory['name']}':\n\n"
        for i, question in enumerate(subcategory['questions'][:5], 1):
            text += f"{i}. {question['question']}\n"
        text += "\nВыберите номер вопроса или вернитесь назад."
        logger.info(f"Сформирован текст вопросов для подкатегории {subcategory['name']}")
        return text
    except IndexError:
        logger.error(f"Неверный индекс при получении текста: cat_index={cat_index}, subcat_index={subcat_index}")
        return "Ошибка: категория не найдена. Вернитесь назад."

# Поиск вопросов по ключевому слову
def search_questions(keyword):
    results = []
    for category in faq_data['categories']:
        for subcategory in category['subcategories']:
            for question in subcategory['questions']:
                if re.search(keyword, question['question'], re.IGNORECASE) or re.search(keyword, question['answer'], re.IGNORECASE):
                    results.append(question)
    logger.info(f"Поиск по '{keyword}': найдено {len(results)} вопросов")
    return results[:5]  # Ограничение на 5 результатов

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        logger.info(f"Получена команда /start от {message.chat.id}")
        bot.reply_to(message, "Добро пожаловать! Я консультант по часто задаваемым вопросам. Выберите категорию:", reply_markup=create_category_buttons())
        logger.info("Категории отправлены")
    except Exception as e:
        logger.error(f"Ошибка при обработке /start: {e}")

# Обработка команды /test (старая функциональность)
@bot.message_handler(commands=['test'])
def send_test(message):
    try:
        logger.info(f"Получена команда /test от {message.chat.id}")
        bot.reply_to(message, "Выберите ответ на тестовый вопрос:", reply_markup=create_test_buttons())
        logger.info("Тестовые кнопки отправлены")
    except Exception as e:
        logger.error(f"Ошибка при обработке /test: {e}")

# Обработка команды /search
@bot.message_handler(commands=['search'])
def start_search(message):
    try:
        logger.info(f"Получена команда /search от {message.chat.id}")
        bot.reply_to(message, "Введите ключевое слово для поиска:")
        bot.register_next_step_handler(message, process_search)
        logger.info("Ожидание ключевого слова")
    except Exception as e:
        logger.error(f"Ошибка при обработке /search: {e}")

# Обработка ключевого слова для поиска
def process_search(message):
    try:
        keyword = message.text.strip()
        logger.info(f"Поиск по ключевому слову: {keyword} от {message.chat.id}")
        results = search_questions(keyword)
        if results:
            text = f"Результаты поиска по '{keyword}':\n\n"
            markup = InlineKeyboardMarkup()
            for i, result in enumerate(results, 1):
                text += f"{i}. {result['question']}\n"
                markup.add(InlineKeyboardButton(f"Вопрос {i}", callback_data=f"q_{result['id']}"))
            markup.add(InlineKeyboardButton("Назад", callback_data="back_to_categories"))
            bot.reply_to(message, text, reply_markup=markup)
        else:
            bot.reply_to(message, f"По запросу '{keyword}' ничего не найдено. Попробуйте другое слово.", reply_markup=create_category_buttons())
        logger.info("Результаты поиска отправлены")
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте снова.", reply_markup=create_category_buttons())

# Обработка callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        logger.info(f"Получен callback: {call.data} от {call.message.chat.id}")
        data = call.data

        # Обработка тестовых кнопок
        if data in ["q1_yes", "q1_no", "q2_good", "q2_bad"]:
            answers = {
                "q1_yes": "Да",
                "q1_no": "Нет",
                "q2_good": "Хорошо",
                "q2_bad": "Плохо"
            }
            bot.answer_callback_query(call.id, f"Вы выбрали: {answers[data]}")
            bot.send_message(call.message.chat.id, f"Спасибо за ответ: {answers[data]}!")
            logger.info(f"Обработан тестовый callback: {data}")
            return

        # Обработка категорий
        if data.startswith("cat_"):
            cat_index = int(data[4:])
            bot.answer_callback_query(call.id)
            category_name = faq_data['categories'][cat_index]['name']
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Выберите подкатегорию в '{category_name}':",
                reply_markup=create_subcategory_buttons(cat_index)
            )
            logger.info(f"Отправлены подкатегории для категории {category_name}")
            return

        # Обработка подкатегорий
        if data.startswith("subcat_"):
            cat_index, subcat_index = map(int, data[7:].split("_"))
            bot.answer_callback_query(call.id)
            subcategory_name = faq_data['categories'][cat_index]['subcategories'][subcat_index]['name']
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=get_questions_text(cat_index, subcat_index),
                reply_markup=create_question_buttons(cat_index, subcat_index)
            )
            logger.info(f"Отправлены вопросы для подкатегории {subcategory_name}")
            return

        # Обработка вопросов
        if data.startswith("q_"):
            question_id = int(data[2:])
            for category in faq_data['categories']:
                for subcategory in category['subcategories']:
                    for question in subcategory['questions']:
                        if question['id'] == question_id:
                            bot.answer_callback_query(call.id)
                            bot.send_message(
                                call.message.chat.id,
                                f"Вопрос: {question['question']}\n\nОтвет: {question['answer']}",
                                reply_markup=create_category_buttons()
                            )
                            logger.info(f"Отправлен ответ на вопрос {question_id}")
                            return
            logger.error(f"Вопрос с id {question_id} не найден")
            bot.answer_callback_query(call.id, "Вопрос не найден")
            return

        # Обработка возврата
        if data == "back_to_categories":
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Выберите категорию:",
                reply_markup=create_category_buttons()
            )
            logger.info("Возврат к категориям")
            return

        if data.startswith("back_to_subcat_"):
            cat_index = int(data[15:])
            category_name = faq_data['categories'][cat_index]['name']
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Выберите подкатегорию в '{category_name}':",
                reply_markup=create_subcategory_buttons(cat_index)
            )
            logger.info(f"Возврат к подкатегориям {category_name}")
            return

        # Обработка поиска
        if data == "search":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "Введите ключевое слово для поиска:")
            bot.register_next_step_handler(call.message, process_search)
            logger.info("Запрошен поиск")
            return

    except Exception as e:
        logger.error(f"Ошибка при обработке callback: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")

# Маршрут для вебхуков
@app.route(f"/{TOKEN}", methods=["POST"])
def get_message():
    try:
        logger.info("Получен POST-запрос от Telegram")
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        if update:
            logger.info(f"Обновление: {update}")
            if update.message and update.message.text and update.message.text.startswith('/start'):
                logger.info(f"Обнаружена команда /start от {update.message.chat.id}")
                send_welcome(update.message)
            else:
                bot.process_new_updates([update])
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
