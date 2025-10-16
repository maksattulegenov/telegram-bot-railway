#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой Telegram бот для сбора данных пользователей и подписей
"""

import json
import base64
import os
import asyncio
import aiohttp
import urllib.parse
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from telegram import WebAppInfo

# Токен бота - читаем из переменных окружения для Railway
BOT_TOKEN = os.getenv('BOT_TOKEN', '7993103484:AAGtwbds-Hzdhpf_lxZr2Xf3YOtvSA1K6VE')

# URL веб-приложения
WEB_APP_URL = "https://railway-web-page-production.up.railway.app"

# n8n Webhook URL
N8N_WEBHOOK_URL = "https://primary-production-7d413.up.railway.app/webhook-test/promed"

# Bot API URL for n8n to send files back
BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Состояния разговора (убрали SIGNATURE, так как подпись идет напрямую в n8n)
FIO, BIRTH_DATE, PHONE, IIN = range(4)

# Создаем папку для подписей
os.makedirs("signatures", exist_ok=True)

# Временное хранилище данных пользователей
user_data_storage = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начальная команда"""
    user_id = update.effective_user.id
    user_data_storage[user_id] = {}
    
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "Я помогу вам заполнить анкету.\n"
        "Для начала, пожалуйста, введите ваше ФИО:"
    )
    return FIO

async def get_fio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем ФИО"""
    user_id = update.effective_user.id
    fio = update.message.text.strip()
    
    print(f"\n📝 === ПОЛУЧЕНИЕ ФИО ОТ ПОЛЬЗОВАТЕЛЯ {user_id} ===")
    print(f"📥 Полученное значение: '{fio}'")
    print(f"📏 Длина строки: {len(fio)} символов")
    
    if len(fio) < 3:
        print(f"❌ ФИО слишком короткое (меньше 3 символов)")
        await update.message.reply_text("❌ Пожалуйста, введите корректное ФИО:")
        return FIO
    
    user_data_storage[user_id]['fio'] = fio
    print(f"✅ ФИО сохранено в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    
    await update.message.reply_text(
        f"✅ ФИО: {fio}\n\n"
        "📅 Теперь введите дату рождения в формате ДД.ММ.ГГГГ\n"
        "Например: 15.05.1990"
    )
    print(f"📤 Запрошена дата рождения у пользователя {user_id}")
    return BIRTH_DATE

async def get_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем дату рождения"""
    user_id = update.effective_user.id
    birth_date = update.message.text.strip()
    
    print(f"\n📅 === ПОЛУЧЕНИЕ ДАТЫ РОЖДЕНИЯ ОТ ПОЛЬЗОВАТЕЛЯ {user_id} ===")
    print(f"📥 Полученное значение: '{birth_date}'")
    print(f"📏 Длина строки: {len(birth_date)} символов")
    
    # Простая проверка формата даты
    try:
        parsed_date = datetime.strptime(birth_date, "%d.%m.%Y")
        print(f"✅ Дата успешно распознана: {parsed_date}")
    except ValueError as e:
        print(f"❌ Ошибка парсинга даты '{birth_date}': {e}")
        await update.message.reply_text("❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ:")
        return BIRTH_DATE
    
    user_data_storage[user_id]['birth_date'] = birth_date
    print(f"✅ Дата рождения сохранена в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    
    await update.message.reply_text(
        f"✅ Дата рождения: {birth_date}\n\n"
        "📱 Теперь введите номер телефона в формате +7XXXXXXXXXX:"
    )
    print(f"📤 Запрошен номер телефона у пользователя {user_id}")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем телефон"""
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    
    print(f"\n📱 === ПОЛУЧЕНИЕ ТЕЛЕФОНА ОТ ПОЛЬЗОВАТЕЛЯ {user_id} ===")
    print(f"📥 Полученное значение: '{phone}'")
    print(f"📏 Длина строки: {len(phone)} символов")
    print(f"🔍 Проверка формата: starts with +7: {phone.startswith('+7')}, length: {len(phone)}, digits after +7: {phone[2:].isdigit() if len(phone) >= 2 else False}")
    
    # Простая проверка телефона
    if not (phone.startswith('+7') and len(phone) == 12 and phone[2:].isdigit()):
        print(f"❌ Неверный формат телефона: '{phone}' (не соответствует +7XXXXXXXXXX)")
        await update.message.reply_text("❌ Неверный формат телефона. Введите в формате +7XXXXXXXXXX:")
        return PHONE
    
    user_data_storage[user_id]['phone'] = phone
    print(f"✅ Телефон сохранен в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    
    await update.message.reply_text(
        f"✅ Телефон: {phone}\n\n"
        "🆔 Теперь введите ИИН (12 цифр):"
    )
    print(f"📤 Запрошен ИИН у пользователя {user_id}")
    return IIN

async def get_iin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем ИИН"""
    user_id = update.effective_user.id
    iin = update.message.text.strip()
    
    print(f"\n🆔 === ПОЛУЧЕНИЕ ИИН ОТ ПОЛЬЗОВАТЕЛЯ {user_id} ===")
    print(f"📥 Полученное значение: '{iin}'")
    print(f"📏 Длина строки: {len(iin)} символов")
    print(f"🔢 Проверка на цифры: {iin.isdigit()}")
    
    # Проверка ИИН
    if not (iin.isdigit() and len(iin) == 12):
        print(f"❌ Неверный формат ИИН: '{iin}' (не 12 цифр или содержит не цифры)")
        await update.message.reply_text("❌ ИИН должен содержать 12 цифр:")
        return IIN
    
    user_data_storage[user_id]['iin'] = iin
    print(f"✅ ИИН сохранен в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    print(f"🎯 Переходим к сбору подписи для пользователя {user_id}")
    
    # Подготавливаем данные для передачи в веб-приложение
    user_data = user_data_storage[user_id].copy()
    user_data['user_id'] = user_id
    user_data['chat_id'] = update.effective_chat.id
    user_data['bot_token'] = BOT_TOKEN
    user_data['n8n_webhook'] = N8N_WEBHOOK_URL
    user_data['bot_api_url'] = BOT_API_URL
    
    # Кодируем данные для URL
    encoded_data = urllib.parse.quote(json.dumps(user_data, ensure_ascii=False))
    web_app_url_with_data = f"{WEB_APP_URL}?data={encoded_data}"
    
    print(f"📦 Передаем данные в веб-приложение:")
    print(f"   ФИО: {user_data['fio']}")
    print(f"   Дата рождения: {user_data['birth_date']}")
    print(f"   Телефон: {user_data['phone']}")
    print(f"   ИИН: {user_data['iin']}")
    print(f"   User ID: {user_data['user_id']}")
    print(f"   Chat ID: {user_data['chat_id']}")
    print(f"🔗 URL веб-приложения: {web_app_url_with_data[:100]}...")
    
    # Создаем кнопку для веб-приложения подписи
    keyboard = [
        [InlineKeyboardButton(
            "✍️ Поставить подпись", 
            web_app=WebAppInfo(url=web_app_url_with_data)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ ИИН: {iin}\n\n"
        "📝 Теперь нужно поставить подпись.\n"
        "Нажмите кнопку ниже, чтобы открыть приложение для подписи.\n"
        "📋 Ваши данные будут переданы в приложение автоматически:",
        reply_markup=reply_markup
    )
    
    # Завершаем разговор, так как подпись будет отправлена напрямую в n8n
    print(f"✅ Завершение разговора для пользователя {user_id}")
    print(f"📤 Данные переданы в веб-приложение для подписи")
    return ConversationHandler.END

async def send_to_webhook(user_data, signature_file_path):
    """Отправляем данные в n8n webhook"""
    print(f"\n📡 === ОТПРАВКА В WEBHOOK ===")
    print(f"🌐 URL: {N8N_WEBHOOK_URL}")
    
    try:
        # Подготавливаем JSON данные
        json_data = {
            "fio": user_data['fio'],
            "date_of_birth": user_data['birth_date'],
            "phone": user_data['phone'],
            "iin": user_data['iin'],
            "timestamp": user_data['timestamp']
        }
        
        print(f"📊 Подготовленные JSON данные:")
        for key, value in json_data.items():
            print(f"   {key}: {value}")
        
        async with aiohttp.ClientSession() as session:
            # 1. Отправляем JSON данные
            print(f"\n📤 ЭТАП 1: Отправка JSON данных...")
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with session.post(N8N_WEBHOOK_URL, json=json_data, timeout=timeout) as response:
                    json_result = await response.text()
                    print(f"📨 Ответ сервера (JSON): HTTP {response.status}")
                    print(f"📄 Содержимое ответа: {json_result[:500]}...")
                    
                    if response.status == 200:
                        print(f"✅ JSON данные успешно отправлены!")
                    else:
                        print(f"⚠️ JSON данные отправлены с кодом {response.status}")
                        
            except asyncio.TimeoutError:
                print(f"⏰ Таймаут при отправке JSON данных")
                return False
            except Exception as json_error:
                print(f"❌ Ошибка отправки JSON: {json_error}")
                return False
            
            # 2. Отправляем файл подписи
            print(f"\n📤 ЭТАП 2: Отправка файла подписи...")
            print(f"📁 Файл: {signature_file_path}")
            
            try:
                with open(signature_file_path, 'rb') as f:
                    file_data = f.read()
                    print(f"📏 Размер файла: {len(file_data)} байт")
                    
                    form_data = aiohttp.FormData()
                    form_data.add_field('signature', file_data, filename=f'signature_{user_data["timestamp"]}.png', content_type='image/png')
                    form_data.add_field('type', 'signature_file')
                    form_data.add_field('user_id', str(user_data.get('user_id', 'unknown')))
                    form_data.add_field('timestamp', str(user_data['timestamp']))
                    
                    print(f"📦 Подготовлены данные формы:")
                    print(f"   - signature: файл PNG ({len(file_data)} байт)")
                    print(f"   - type: signature_file")
                    print(f"   - user_id: {user_data.get('user_id', 'unknown')}")
                    print(f"   - timestamp: {user_data['timestamp']}")
                    
                    timeout = aiohttp.ClientTimeout(total=30)
                    async with session.post(N8N_WEBHOOK_URL, data=form_data, timeout=timeout) as response:
                        file_result = await response.text()
                        print(f"📨 Ответ сервера (файл): HTTP {response.status}")
                        print(f"📄 Содержимое ответа: {file_result[:500]}...")
                        
                        if response.status == 200:
                            print(f"✅ Файл подписи успешно отправлен!")
                        else:
                            print(f"⚠️ Файл подписи отправлен с кодом {response.status}")
                            
            except asyncio.TimeoutError:
                print(f"⏰ Таймаут при отправке файла")
                return False
            except Exception as file_error:
                print(f"❌ Ошибка отправки файла: {file_error}")
                return False
        
        print(f"🎉 ВСЕ ДАННЫЕ УСПЕШНО ОТПРАВЛЕНЫ В WEBHOOK!")
        return True
        
    except Exception as e:
        print(f"❌ Общая ошибка webhook: {e}")
        return False

# REMOVED: handle_signature function
# Now signature data goes directly from web app to n8n webhook
# No need to process it through the bot

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать помощь"""
    user_id = update.effective_user.id
    
    await update.message.reply_text(
        "🤖 *Бот для сбора данных пользователей*\n\n"
        "*Команды:*\n"
        "• /start - Начать заполнение анкеты\n"
        "• /help - Показать эту справку\n"
        "• /cancel - Отменить заполнение анкеты\n\n"
        "*Процесс заполнения:*\n"
        "• ФИО\n"
        "• Дата рождения (ДД.ММ.ГГГГ)\n"
        "• Телефон (+7XXXXXXXXXX)\n"
        "• ИИН (12 цифр)\n"
        "• Подпись (через веб-приложение)\n\n"
        "📝 Данные передаются напрямую в систему через веб-приложение",
        parse_mode='Markdown'
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    user_id = update.effective_user.id
    if user_id in user_data_storage:
        del user_data_storage[user_id]
    
    await update.message.reply_text(
        "❌ Операция отменена. Для начала заново отправьте /start"
    )
    return ConversationHandler.END

def main():
    """Запуск бота"""
    print("🤖 Запуск бота...")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Создаем обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fio)],
            BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_birth_date)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            IIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_iin)],
            # SIGNATURE state removed - signature goes directly to n8n
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(conv_handler)
    
    # Removed separate web app data handler - not needed anymore
    
    application.add_handler(CommandHandler('help', help_command))
    
    print(f"✅ Бот запущен! Веб-приложение: {WEB_APP_URL}")
    print("📁 Подписи будут сохраняться в папку 'signatures/'")
    print("📄 Данные пользователей сохраняются в JSON файлы")
    print("🛑 Для остановки нажмите Ctrl+C")
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()