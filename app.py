import telebot
from telebot import types
import uuid
import sqlite3
import re
from datetime import datetime
import requests

API_TOKEN = '7999432085:AAHcK3_UURkeoPtyEfNJjwJeLGSK3WgNu5o'
ADMIN_BOT_API_TOKEN = '8126103952:AAGSX9IZcjAoHI1VVLgmztUGrfv_QJMIBvk'
ADMIN_BOT_CHAT_ID = '6903472998'

bot = telebot.TeleBot(API_TOKEN)

# Настройка базы данных
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    phone TEXT,
    code TEXT,
    registration_date TEXT
)''')
conn.commit()

user_data = {}

# Логирование событий
def log_event(event):
    with open('bot_logs.txt', 'a') as log_file:
        log_file.write(f"{datetime.now()} - {event}\n")

@bot.message_handler(commands=['start', 'help'])
def start(message):
    commands_list = (
        "/register - Регистрация\n"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Регистрация')
    bot.send_message(message.chat.id, "Добро пожаловать! Доступные команды:\n" + commands_list, reply_markup=markup)
    log_event(f"User {message.chat.id} started or requested help.")

@bot.message_handler(func=lambda message: message.text.strip().lower() == 'регистрация')
def registration(message):
    user_data[message.chat.id] = {}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Отмена')
    bot.send_message(message.chat.id, 'Введите ваше имя:', reply_markup=markup)
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    if message.text.strip().lower() == 'отмена':
        cancel(message)
        return
    user_data[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, 'Введите ваш номер телефона (только цифры):')
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    if message.text.strip().lower() == 'отмена':
        cancel(message)
        return
    phone_number = message.text
    if not re.match(r'^\d{10,15}$', phone_number):
        bot.send_message(message.chat.id, 'Неверный формат телефона. Попробуйте снова.')
        bot.register_next_step_handler(message, get_phone)
        return

    user_data[message.chat.id]['phone'] = phone_number

    # Генерация уникального кода
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    user_code = f"A1{400 + user_count}"
    user_data[message.chat.id]['code'] = user_code
    user_data[message.chat.id]['registration_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Сохранение данных в базу данных
    cursor.execute('''INSERT INTO users (user_id, name, phone, code, registration_date) VALUES (?, ?, ?, ?, ?)''',
                   (message.chat.id, user_data[message.chat.id]['name'], user_data[message.chat.id]['phone'], user_code, user_data[message.chat.id]['registration_date']))
    conn.commit()

    # Отправка данных в администраторский бот через API
    try:
        requests.post(f"https://api.telegram.org/bot{ADMIN_BOT_API_TOKEN}/sendMessage", data={
            "chat_id": ADMIN_BOT_CHAT_ID,
            "text": f"Новый пользователь зарегистрировался:\n"
                    f"Имя: {user_data[message.chat.id]['name']}\n"
                    f"Телефон: {user_data[message.chat.id]['phone']}\n"
                    f"Код: {user_code}"
        })
    except Exception as e:
        log_event(f"Ошибка отправки данных в админ-бот через API: {e}")

    # Отправка сообщения пользователю
    address_message = (f"Ваш адрес для доставки:\n"
                       f"广东省佛山市南海区里水镇环镇南路33号1号仓315库B6961\n"
                       f"收货人 梅先生-B6961\n"
                       f"Телефон: 13250150777\n"
                       f"Ссылка: https://t.me/+N1Xktz9wb55jZjRi\n"
                       f"Ваш уникальный код: {user_code}")

    bot.send_message(message.chat.id, address_message)

    # Отправка двух видео
    video_paths = ['instruction.mp4', 'instructions.mp4']
    for path in video_paths:
        try:
            with open(path, 'rb') as video:
                bot.send_video(message.chat.id, video)
        except FileNotFoundError:
            bot.send_message(message.chat.id, f'Видео {path} временно недоступно.')
        except Exception as e:
            log_event(f"Ошибка отправки видео {path}: {e}")

    bot.send_message(message.chat.id, "Регистрация завершена!", reply_markup=types.ReplyKeyboardRemove())
    log_event(f"User {message.chat.id} registered with code {user_code}.")
    del user_data[message.chat.id]

def cancel(message):
    bot.send_message(message.chat.id, 'Регистрация отменена.', reply_markup=types.ReplyKeyboardRemove())
    log_event(f"User {message.chat.id} cancelled registration.")
    if message.chat.id in user_data:
        del user_data[message.chat.id]

if __name__ == '__main__':
    bot.infinity_polling()
