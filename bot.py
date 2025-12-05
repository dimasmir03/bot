import threading
import time
import sqlite3
import telebot
from telebot import types
from datetime import datetime
import random
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле!")

DB_NAME = "birthdays.db"

Conn = sqlite3.Connect(DB_NAME)
C = Conn.cursor()

def init_db():
    C.execute("""
    CREATE TABLE IF NOT EXISTS birthdays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        date TEXT
    )
    """)
    Conn.commit()

init_db()
os.makedirs("images", exist_ok=True)

birthday_texts = [
    "🎉 {name}, с днём рождения! Желаю счастья, здоровья и исполнения всех желаний!",
    "🎂 Поздравляю тебя, {name}! Пусть этот год будет самым лучшим!",
    "🎈 {name}, с праздником! Желаю улыбок, радости и море позитива!",
    "🎁 С днём рождения, {name}! Пусть сбудутся все мечты!",
    "🌟 {name}, поздравляю! Желаю вдохновения и незабываемых моментов!"
]

gift_ideas = [
    "Идея подарка: Книга по интересам",
    "Идея подарка: Сертификат в SPA или массаж",
    "Идея подарка: Настольная игра для компании",
    "Идея подарка: Беспроводные наушники",
    "Идея подарка: Абонемент в спортзал",
    "Идея подарка: Набор для хобби (рисование, вязание)",
    "Идея подарка: Умная колонка или гаджет",
    "Идея подарка: Поход в ресторан или квест-комнату",
    "Идея подарка: Фотосессия с профессионалом",
    "Идея подарка: Подписка на онлайн-курс"
]

def get_birthday_text(name):
    return random.choice(birthday_texts).format(name=name)

def get_gift_idea():
    return random.choice(gift_ideas)

image_files = []

def refresh_image_files():
    global image_files
    image_files = [f for f in os.listdir("images") if f.endswith(('.jpg', '.png', '.jpeg'))]

def get_random_image():
    refresh_image_files()
    if image_files:
        return os.path.join("images", random.choice(image_files))
    return None

def add_birthday(user_id, name, date):
    C.execute("INSERT INTO birthdays (user_id, name, date) VALUES (?, ?, ?)", (user_id, name, date))
    Conn.commit()

def get_birthdays(user_id):
    C.execute("SELECT id, name, date FROM birthdays WHERE user_id=?", (user_id,))
    rows = C.fetchall()
    return rows

def delete_birthday(entry_id):
    C.execute("DELETE FROM birthdays WHERE id=?", (entry_id,))
    Conn.commit()

def update_birthday(entry_id, new_name, new_date):
    C.execute("UPDATE birthdays SET name=?, date=? WHERE id=?", (new_name, new_date, entry_id))
    Conn.commit()

user_state = {}

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Добавить дату", "Показать даты")
    kb.add("Изменить", "Удалить")
    kb.add("Поздравление", "Идея подарка")
    kb.add("Картинка")
    return kb

def handle_birthday_features(message):
    user_id = message.chat.id
    text = message.text
    
    if text == "Поздравление":
        entries = get_birthdays(user_id)
        if not entries:
            bot.send_message(user_id, "У тебя нет записей. Сначала добавь кого-нибудь!")
            return True
        
        user_state[user_id] = {"action": "send_congratulation"}
        msg = "Выбери ID человека для поздравления:\n\n"
        for row in entries:
            msg += f"ID {row[0]} — {row[1]}\n"
        bot.send_message(user_id, msg)
        return True
    
    if text == "Идея подарка":
        gift = get_gift_idea()
        bot.send_message(user_id, gift)
        return True
    
    if text == "Картинка":
        image_path = get_random_image()
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                bot.send_photo(user_id, photo, caption="Поздравительная открытка!")
        else:
            bot.send_message(user_id, "Картинки не найдены. Загрузи их в папку images/")
        return True
    
    return False

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Это бот с напоминаниями о днях рождения. Выбери действие:",
        reply_markup=main_keyboard()
    )

@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.chat.id
    text = message.text

    if handle_birthday_features(message):
        return

    if text == "Добавить дату":
        user_state[user_id] = {"action": "add_name"}
        bot.send_message(user_id, "Введи имя:")
        return

    if text == "Показать даты":
        entries = get_birthdays(user_id)
        if not entries:
            bot.send_message(user_id, "У тебя нет записей.")
            return

        msg = "Твои записи:\n\n"
        for row in entries:
            msg += f"ID {row[0]} — {row[1]}, {row[2]}\n"
        bot.send_message(user_id, msg)
        return

    if text == "Удалить":
        user_state[user_id] = {"action": "delete"}
        bot.send_message(user_id, "Введи ID для удаления:")
        return

    if text == "Изменить":
        user_state[user_id] = {"action": "edit_select"}
        bot.send_message(user_id, "Введи ID для изменения:")
        return

    if user_id in user_state and user_state[user_id]["action"] == "send_congratulation":
        try:
            C.execute("SELECT name FROM birthdays WHERE id=? AND user_id=?", (int(text), user_id))
            result = C.fetchone()
            
            if result:
                name = result[0]
                congrats_text = get_birthday_text(name)
                bot.send_message(user_id, congrats_text, reply_markup=main_keyboard())
            else:
                bot.send_message(user_id, "ID не найден.")
        except:
            bot.send_message(user_id, "Ошибка. ID должен быть числом.")
        
        del user_state[user_id]
        return

    if user_id in user_state and user_state[user_id]["action"] == "add_name":
        user_state[user_id] = {"action": "add_date", "name": text}
        bot.send_message(user_id, "Введи дату (дд.мм.гггг):")
        return

    if user_id in user_state and user_state[user_id]["action"] == "add_date":
        try:
            datetime.strptime(text, "%d.%m.%Y")
        except:
            bot.send_message(user_id, "Неверный формат. Пример: 04.12.2001")
            return

        name = user_state[user_id]["name"]
        add_birthday(user_id, name, text)
        bot.send_message(user_id, "Готово!", reply_markup=main_keyboard())
        del user_state[user_id]
        return

    if user_id in user_state and user_state[user_id]["action"] == "delete":
        try:
            delete_birthday(int(text))
            bot.send_message(user_id, "Удалено.", reply_markup=main_keyboard())
        except:
            bot.send_message(user_id, "Ошибка — неверный ID.")
        del user_state[user_id]
        return

    if user_id in user_state and user_state[user_id]["action"] == "edit_select":
        try:
            edit_id = int(text)
        except:
            bot.send_message(user_id, "ID должен быть числом.")
            return

        user_state[user_id] = {"action": "edit_name", "edit_id": edit_id}
        bot.send_message(user_id, "Введи новое имя:")
        return

    if user_id in user_state and user_state[user_id]["action"] == "edit_name":
        user_state[user_id]["new_name"] = text
        user_state[user_id]["action"] = "edit_date"
        bot.send_message(user_id, "Новая дата (дд.мм.гггг):")
        return

    if user_id in user_state and user_state[user_id]["action"] == "edit_date":
        try:
            datetime.strptime(text, "%d.%m.%Y")
        except:
            bot.send_message(user_id, "Неверный формат даты.")
            return

        data = user_state[user_id]
        update_birthday(data["edit_id"], data["new_name"], text)
        bot.send_message(user_id, "Обновлено!", reply_markup=main_keyboard())
        del user_state[user_id]
        return

def check_today_birthdays():
    today = datetime.now().strftime("%d.%m")
    
    C.execute("SELECT user_id, name, date FROM birthdays")
    rows = C.fetchall()

    for user_id, name, full_date in rows:
        try:
            date_obj = datetime.strptime(full_date, "%d.%m.%Y")
            birthday_day_month = date_obj.strftime("%d.%m")
            
            if birthday_day_month == today:
                text = get_birthday_text(name)
                bot.send_message(user_id, text)
                
                image_path = get_random_image()
                if image_path and os.path.exists(image_path):
                    with open(image_path, 'rb') as photo:
                        bot.send_photo(user_id, photo)
                
                gift = get_gift_idea()
                bot.send_message(user_id, gift)
                    
        except Exception as e:
            print(f"Ошибка отправки: {e}")

def birthday_checker_loop():
    last_date = None
    while True:
        now = datetime.now().strftime("%d.%m.%Y")
        if now != last_date:
            last_date = now
            check_today_birthdays()
        time.sleep(60)

threading.Thread(target=birthday_checker_loop, daemon=True).start()

if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
