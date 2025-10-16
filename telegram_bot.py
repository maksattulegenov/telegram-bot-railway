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
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes, CallbackQueryHandler
from telegram import WebAppInfo, WebAppData

# Токен бота - читаем из переменных окружения для Railway
BOT_TOKEN = os.getenv('BOT_TOKEN', '7993103484:AAGtwbds-Hzdhpf_lxZr2Xf3YOtvSA1K6VE')

# URL веб-приложения
WEB_APP_URL = "https://railway-web-page-production.up.railway.app"

# n8n Webhook URL
N8N_WEBHOOK_URL = "https://primary-production-7d413.up.railway.app/webhook-test/promed"

# Bot API URL for n8n to send files back
BOT_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Состояния разговора (убрали SIGNATURE, так как подпись идет напрямую в n8n)
FIO, BIRTH_DATE, GENDER, IIN, PHONE, EXAMINATION_FOR, ALLERGY, PROHIBITED_PROCEDURES, CONTACT_PERSON, MINOR_CONSENT, PATIENT_REPRESENTATIVE = range(11)

# Создаем папку для подписей
os.makedirs("signatures", exist_ok=True)

# Временное хранилище данных пользователей
user_data_storage = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начальная команда"""
    user_id = update.effective_user.id
    user_data_storage[user_id] = {}
    
    await update.message.reply_text(
        "Добровольное информированное согласие пациента на оказание медицинских услуг на платной основе в ТОО «PRO-MED Clinic»\n\n"
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
        await update.message.reply_text("Пожалуйста, введите корректное ФИО:")
        return FIO
    
    user_data_storage[user_id]['fio'] = fio
    print(f"✅ ФИО сохранено в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    
    await update.message.reply_text(
        f"ФИО: {fio}\n\n"
        "Теперь введите дату рождения в формате ДД.ММ.ГГГГ\n"
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
        await update.message.reply_text("Неверный формат даты. Введите в формате ДД.ММ.ГГГГ:")
        return BIRTH_DATE
    
    user_data_storage[user_id]['birth_date'] = birth_date
    print(f"✅ Дата рождения сохранена в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    
    # Переходим к выбору пола
    keyboard = [
        [InlineKeyboardButton("Мужчина", callback_data="gender_male")],
        [InlineKeyboardButton("Женщина", callback_data="gender_female")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Дата рождения: {birth_date}\n\n"
        "Укажите пол:",
        reply_markup=reply_markup
    )
    return GENDER

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем телефон"""
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    
    print(f"\n📱 === ПОЛУЧЕНИЕ ТЕЛЕФОНА ОТ ПОЛЬЗОВАТЕЛЯ {user_id} ===")
    print(f"📥 Полученное значение: '{phone}'")
    print(f"📏 Длина строки: {len(phone)} символов")
    print(f"🔍 Проверка формата: starts with 8: {phone.startswith('8')}, length: {len(phone)}, digits after 8: {phone[1:].isdigit() if len(phone) >= 1 else False}")
    
    # Простая проверка телефона (должен начинаться с 8 и содержать 11 цифр)
    if not (phone.startswith('8') and len(phone) == 11 and phone[1:].isdigit()):
        print(f"❌ Неверный формат телефона: '{phone}' (не соответствует 8XXXXXXXXXX)")
        await update.message.reply_text("Неверный формат телефона. Введите в формате 8XXXXXXXXXX:")
        return PHONE
    
    user_data_storage[user_id]['phone'] = phone
    print(f"✅ Телефон сохранен в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    
    # Переходим к выбору "на обследование кому"
    keyboard = [
        [InlineKeyboardButton("Себе", callback_data="exam_self")],
        [InlineKeyboardButton("Ребенку", callback_data="exam_child")],
        [InlineKeyboardButton("Родственнику", callback_data="exam_relative")],
        [InlineKeyboardButton("Подопечному", callback_data="exam_ward")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Телефон: {phone}\n\n"
        "На обследование кому:",
        reply_markup=reply_markup
    )
    return EXAMINATION_FOR

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
        await update.message.reply_text("ИИН должен содержать 12 цифр:")
        return IIN
    
    user_data_storage[user_id]['iin'] = iin
    print(f"✅ ИИН сохранен в память")
    print(f"📊 Текущие данные пользователя: {user_data_storage[user_id]}")
    
    await update.message.reply_text(
        f"ИИН: {iin}\n\n"
        "Теперь введите номер телефона в формате 8XXXXXXXXXX:"
    )
    print(f"📤 Запрошен номер телефона у пользователя {user_id}")
    return PHONE

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем пол через callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    gender = "Мужчина" if query.data == "gender_male" else "Женщина"
    
    user_data_storage[user_id]['gender'] = gender
    print(f"✅ Пол сохранен: {gender}")
    
    await query.edit_message_text(
        f"Пол: {gender}\n\n"
        "Теперь введите ИИН (12 цифр):"
    )
    return IIN

async def get_examination_for(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем информацию о том, для кого обследование"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    examination_for_map = {
        "exam_self": "себе",
        "exam_child": "ребенку", 
        "exam_relative": "родственнику",
        "exam_ward": "подопечному"
    }
    
    examination_for = examination_for_map[query.data]
    user_data_storage[user_id]['examination_for'] = examination_for
    user_data_storage[user_id]['examination_for_key'] = query.data  # Сохраняем ключ для использования в следующих вопросах
    
    print(f"✅ Обследование для: {examination_for}")
    
    # Если обследование не для себя, спрашиваем о представителе пациента
    if query.data != "exam_self":
        await query.edit_message_text(
            f"На обследование: {examination_for}\n\n"
            "Если заполнил родственник / опекун / законный представитель пациента:\n"
            "Введите ФИО представителя:"
        )
        return PATIENT_REPRESENTATIVE
    else:
        # Переходим к вопросу об аллергии
        keyboard = [
            [InlineKeyboardButton("Нет аллергии", callback_data="no_allergy")],
            [InlineKeyboardButton("Есть аллергия", callback_data="has_allergy")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"На обследование: {examination_for}\n\n"
            "Я сообщаю о том, что у меня:",
            reply_markup=reply_markup
        )
        return ALLERGY

async def get_patient_representative(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем информацию о представителе пациента"""
    user_id = update.effective_user.id
    
    # Проверяем, первый ли это вызов (ФИО) или второй (степень родства)
    if 'representative_fio' not in user_data_storage[user_id]:
        # Первый вызов - получаем ФИО
        representative_fio = update.message.text.strip()
        user_data_storage[user_id]['representative_fio'] = representative_fio
        
        await update.message.reply_text(
            f"ФИО представителя: {representative_fio}\n\n"
            "Укажите степень родства:"
        )
        return PATIENT_REPRESENTATIVE
    else:
        # Второй вызов - получаем степень родства
        relation = update.message.text.strip()
        user_data_storage[user_id]['representative_relation'] = relation
        
        # Формируем текст в зависимости от того, для кого обследование
        examination_for_key = user_data_storage[user_id].get('examination_for_key', 'exam_self')
        person_text = {
            "exam_child": "у ребенка",
            "exam_relative": "у родственника", 
            "exam_ward": "у подопечного"
        }
        
        # Переходим к вопросу об аллергии
        keyboard = [
            [InlineKeyboardButton("Нет аллергии", callback_data="no_allergy")],
            [InlineKeyboardButton("Есть аллергия", callback_data="has_allergy")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Степень родства: {relation}\n\n"
            f"Я сообщаю о том, что {person_text.get(examination_for_key, 'у пациента')}:",
            reply_markup=reply_markup
        )
        return ALLERGY

async def get_allergy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем информацию об аллергии"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "no_allergy":
        user_data_storage[user_id]['allergy'] = "Нет аллергии"
        print(f"✅ Аллергия: Нет")
        
        # Переходим к запрещенным процедурам
        await query.edit_message_text(
            "Аллергии нет\n\n"
            "Ни при каких обстоятельствах мне не должны выполняться следующие процедуры:\n\n"
            "Укажите процедуры, если вы против их выполнения. Если нет таковых – напишите \"нет\":"
        )
        return PROHIBITED_PROCEDURES
    else:
        # Запрашиваем подробности об аллергии
        await query.edit_message_text(
            "Есть аллергия\n\n"
            "Пожалуйста, укажите на какие лекарства, продукты есть аллергия:"
        )
        user_data_storage[user_id]['allergy_status'] = "has_allergy"
        return ALLERGY

async def get_allergy_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем детали аллергии"""
    user_id = update.effective_user.id
    allergy_details = update.message.text.strip()
    
    user_data_storage[user_id]['allergy'] = f"Есть аллергия на: {allergy_details}"
    print(f"✅ Аллергия сохранена: {allergy_details}")
    
    await update.message.reply_text(
        f"Аллергия: {allergy_details}\n\n"
        "Ни при каких обстоятельствах мне не должны выполняться следующие процедуры:\n\n"
        "Укажите процедуры, если вы против их выполнения. Если нет таковых – напишите \"нет\":"
    )
    return PROHIBITED_PROCEDURES

async def get_prohibited_procedures(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем информацию о запрещенных процедурах"""
    user_id = update.effective_user.id
    prohibited = update.message.text.strip()
    
    if prohibited.lower() in ['нет', 'нету', '']:
        user_data_storage[user_id]['prohibited_procedures'] = "Нет запрещенных процедур"
    else:
        user_data_storage[user_id]['prohibited_procedures'] = prohibited
    
    print(f"✅ Запрещенные процедуры: {user_data_storage[user_id]['prohibited_procedures']}")
    
    # Формируем текст в зависимости от того, для кого обследование
    examination_for_key = user_data_storage[user_id].get('examination_for_key', 'exam_self')
    person_text = {
        "exam_self": "моего",
        "exam_child": "ребенка", 
        "exam_relative": "родственника",
        "exam_ward": "подопечного"
    }
    
    await update.message.reply_text(
        f"Запрещенные процедуры: {user_data_storage[user_id]['prohibited_procedures']}\n\n"
        f"Любую информацию о состоянии {person_text[examination_for_key]} здоровья, проводимом обследовании и лечении, его результатах я разрешаю сообщать следующим лицам:\n\n"
        "Введите ФИО лица, которому вы разрешаете сообщать о ходе лечения (или напишите \"нет\" если таких нет):"
    )
    return CONTACT_PERSON

async def get_contact_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем информацию о контактном лице"""
    user_id = update.effective_user.id
    contact_fio = update.message.text.strip()
    
    if contact_fio.lower() in ['нет', 'нету']:
        user_data_storage[user_id]['contact_person'] = {
            'fio': 'Нет',
            'relation': 'Нет', 
            'phone': 'Нет'
        }
        
        # Проверяем, нужен ли вопрос о несовершеннолетнем
        examination_for_key = user_data_storage[user_id].get('examination_for_key', 'exam_self')
        if examination_for_key == 'exam_child':
            await update.message.reply_text(
                "✅ Контактное лицо: Нет\n\n"
                "👶 Если пациент младше 18 лет: даю разрешение получать дополнительные согласия на проведение лечебных и диагностических манипуляций высокого риска при моем отсутствии у вышеуказанных лиц по вышеуказанным телефонам:"
            )
            
            keyboard = [
                [InlineKeyboardButton("✅ Да", callback_data="minor_yes")],
                [InlineKeyboardButton("❌ Нет", callback_data="minor_no")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text("Выберите вариант:", reply_markup=reply_markup)
            return MINOR_CONSENT
        else:
            return await finish_data_collection(update, context)
    else:
        user_data_storage[user_id]['contact_person_fio'] = contact_fio
        await update.message.reply_text(
            f"✅ ФИО контактного лица: {contact_fio}\n\n"
            "👥 Укажите родство/отношение к пациенту:"
        )
        return CONTACT_PERSON

async def get_contact_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем отношение к пациенту"""
    user_id = update.effective_user.id
    relation = update.message.text.strip()
    
    user_data_storage[user_id]['contact_person_relation'] = relation
    
    await update.message.reply_text(
        f"Отношение: {relation}\n\n"
        "Укажите телефон контактного лица:"
    )
    return CONTACT_PERSON

async def get_contact_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем телефон контактного лица"""
    user_id = update.effective_user.id
    contact_phone = update.message.text.strip()
    
    user_data_storage[user_id]['contact_person'] = {
        'fio': user_data_storage[user_id].get('contact_person_fio', ''),
        'relation': user_data_storage[user_id].get('contact_person_relation', ''),
        'phone': contact_phone
    }
    
    # Очищаем временные поля
    user_data_storage[user_id].pop('contact_person_fio', None)
    user_data_storage[user_id].pop('contact_person_relation', None)
    
    print(f"✅ Контактное лицо сохранено: {user_data_storage[user_id]['contact_person']}")
    
    # Проверяем, нужен ли вопрос о несовершеннолетнем
    examination_for_key = user_data_storage[user_id].get('examination_for_key', 'exam_self')
    if examination_for_key == 'exam_child':
        keyboard = [
            [InlineKeyboardButton("Да", callback_data="minor_yes")],
            [InlineKeyboardButton("Нет", callback_data="minor_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Телефон контактного лица: {contact_phone}\n\n"
            "Если пациент младше 18 лет: даю разрешение получать дополнительные согласия на проведение лечебных и диагностических манипуляций высокого риска при моем отсутствии у вышеуказанных лиц по вышеуказанным телефонам:",
            reply_markup=reply_markup
        )
        return MINOR_CONSENT
    else:
        return await finish_data_collection(update, context)

async def get_minor_consent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем согласие для несовершеннолетнего"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    consent = "Да" if query.data == "minor_yes" else "Нет"
    
    user_data_storage[user_id]['minor_consent'] = consent
    print(f"✅ Согласие для несовершеннолетнего: {consent}")
    
    await query.edit_message_text(f"Разрешение для несовершеннолетнего: {consent}")
    
    return await finish_data_collection(update, context)

async def get_minor_consent_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем согласие для несовершеннолетнего через текстовое сообщение"""
    user_id = update.effective_user.id
    text_input = update.message.text.strip().lower()
    
    # Проверяем различные варианты "да" и "нет" на русском
    if text_input in ['да', 'yes', 'д', 'y', '1', '+']:
        consent = "Да"
    elif text_input in ['нет', 'no', 'н', 'n', '0', '-']:
        consent = "Нет"
    else:
        # Если ввод неопознан, предлагаем использовать кнопки
        keyboard = [
            [InlineKeyboardButton("Да", callback_data="minor_yes")],
            [InlineKeyboardButton("Нет", callback_data="minor_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Пожалуйста, выберите один из вариантов ниже или используйте кнопки:",
            reply_markup=reply_markup
        )
        return MINOR_CONSENT
    
    user_data_storage[user_id]['minor_consent'] = consent
    print(f"✅ Согласие для несовершеннолетнего (текст): {consent}")
    
    await update.message.reply_text(f"Разрешение для несовершеннолетнего: {consent}")
    
    return await finish_data_collection(update, context)

async def handle_contact_person_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем поток ввода контактного лица"""
    user_id = update.effective_user.id
    user_input = update.message.text.strip()
    
    # Проверяем, на каком этапе мы находимся для представителя пациента
    if 'representative_fio' in user_data_storage[user_id] and 'representative_relation' not in user_data_storage[user_id]:
        # Обрабатываем степень родства представителя через основную функцию
        return await get_patient_representative(update, context)
    
    # Проверяем, на каком этапе мы находимся для контактного лица
    if 'contact_person_fio' not in user_data_storage[user_id]:
        # Первый этап - ФИО
        return await get_contact_person(update, context)
    elif 'contact_person_relation' not in user_data_storage[user_id]:
        # Второй этап - отношение
        return await get_contact_relation(update, context)
    else:
        # Третий этап - телефон
        return await get_contact_phone(update, context)

async def finish_data_collection(update, context):
    """Завершаем сбор данных и переходим к подписи"""
    user_id = update.effective_user.id if hasattr(update, 'effective_user') else update.callback_query.from_user.id
    chat_id = update.effective_chat.id if hasattr(update, 'effective_chat') else update.callback_query.message.chat.id
    
    print(f"🎯 Переходим к сбору подписи для пользователя {user_id}")
    
    # Подготавливаем данные для передачи в веб-приложение
    user_data = user_data_storage[user_id].copy()
    user_data['user_id'] = user_id
    user_data['chat_id'] = chat_id
    user_data['bot_token'] = BOT_TOKEN
    user_data['n8n_webhook'] = N8N_WEBHOOK_URL
    user_data['bot_api_url'] = BOT_API_URL
    
    # Добавляем timestamp если его нет
    if 'timestamp' not in user_data:
        user_data['timestamp'] = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Кодируем данные для URL
    encoded_data = urllib.parse.quote(json.dumps(user_data, ensure_ascii=False))
    web_app_url_with_data = f"{WEB_APP_URL}?data={encoded_data}"
    
    print(f"📦 Передаем данные в веб-приложение:")
    for key, value in user_data.items():
        if key not in ['bot_token', 'n8n_webhook', 'bot_api_url']:
            print(f"   {key}: {value}")
    
    print(f"🔗 URL длина: {len(web_app_url_with_data)} символов")
    print(f"🔗 Encoded data длина: {len(encoded_data)} символов")
    
    # Создаем кнопку для веб-приложения подписи
    keyboard = [
        [InlineKeyboardButton(
            "Поставить подпись", 
            web_app=WebAppInfo(url=web_app_url_with_data)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "Все данные собраны!\n\n"
        "Теперь нужно поставить подпись.\n"
        "Нажмите кнопку ниже, чтобы открыть приложение для подписи.\n"
        "Ваши данные будут переданы в приложение автоматически."
    )
    
    if hasattr(update, 'message'):
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(message_text, reply_markup=reply_markup)
    
    # Завершаем разговор, так как подпись будет отправлена напрямую в n8n
    print(f"✅ Завершение разговора для пользователя {user_id}")
    print(f"📤 Данные переданы в веб-приложение для подписи")
    return ConversationHandler.END
    """Завершаем сбор данных и переходим к подписи"""
    user_id = update.effective_user.id if hasattr(update, 'effective_user') else update.callback_query.from_user.id
    chat_id = update.effective_chat.id if hasattr(update, 'effective_chat') else update.callback_query.message.chat.id
    
    print(f"🎯 Переходим к сбору подписи для пользователя {user_id}")
    
    # Подготавливаем данные для передачи в веб-приложение
    user_data = user_data_storage[user_id].copy()
    user_data['user_id'] = user_id
    user_data['chat_id'] = chat_id
    user_data['bot_token'] = BOT_TOKEN
    user_data['n8n_webhook'] = N8N_WEBHOOK_URL
    user_data['bot_api_url'] = BOT_API_URL
    
    # Кодируем данные для URL
    encoded_data = urllib.parse.quote(json.dumps(user_data, ensure_ascii=False))
    web_app_url_with_data = f"{WEB_APP_URL}?data={encoded_data}"
    
    print(f"� Передаем данные в веб-приложение:")
    for key, value in user_data.items():
        if key not in ['bot_token', 'n8n_webhook', 'bot_api_url']:
            print(f"   {key}: {value}")
    
    # Создаем кнопку для веб-приложения подписи
    keyboard = [
        [InlineKeyboardButton(
            "✍️ Поставить подпись", 
            web_app=WebAppInfo(url=web_app_url_with_data)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "✅ Все данные собраны!\n\n"
        "📝 Теперь нужно поставить подпись.\n"
        "Нажмите кнопку ниже, чтобы открыть приложение для подписи.\n"
        "📋 Ваши данные будут переданы в приложение автоматически."
    )
    
    if hasattr(update, 'message'):
        await update.message.reply_text(message_text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(message_text, reply_markup=reply_markup)
    
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
            "gender": user_data.get('gender', ''),
            "iin": user_data['iin'],
            "phone": user_data['phone'],
            "examination_for": user_data.get('examination_for', ''),
            "representative_fio": user_data.get('representative_fio', ''),
            "representative_relation": user_data.get('representative_relation', ''),
            "allergy": user_data.get('allergy', ''),
            "prohibited_procedures": user_data.get('prohibited_procedures', ''),
            "contact_person": user_data.get('contact_person', {}),
            "minor_consent": user_data.get('minor_consent', ''),
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
        "Бот для сбора данных пользователей\n\n"
        "Команды:\n"
        "• /start - Начать заполнение анкеты\n"
        "• /help - Показать эту справку\n"
        "• /cancel - Отменить заполнение анкеты\n\n"
        "Процесс заполнения:\n"
        "• ФИО\n"
        "• Дата рождения (ДД.ММ.ГГГГ)\n"
        "• Пол (мужчина/женщина)\n"
        "• ИИН (12 цифр)\n"
        "• Телефон (8XXXXXXXXXX)\n"
        "• Для кого обследование (себе/ребенку/родственнику/подопечному)\n"
        "• Представитель пациента (при необходимости)\n"
        "• Информация об аллергии\n"
        "• Запрещенные процедуры\n"
        "• Контактное лицо для получения информации\n"
        "• Согласие для несовершеннолетних (при необходимости)\n"
        "• Подпись (через веб-приложение)\n\n"
        "Данные передаются напрямую в систему через веб-приложение",
        parse_mode='Markdown'
    )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем данные от веб-приложения после завершения подписи"""
    try:
        # Получаем данные от веб-приложения
        web_app_data = update.effective_message.web_app_data.data
        data = json.loads(web_app_data)
        
        user_id = update.effective_user.id
        print(f"📱 === ПОЛУЧЕНЫ ДАННЫЕ ОТ ВЕБ-ПРИЛОЖЕНИЯ ДЛЯ ПОЛЬЗОВАТЕЛЯ {user_id} ===")
        print(f"📊 Данные: {data}")
        
        # Проверяем, что это завершение подписи
        if data.get('action') == 'signature_completed':
            await update.effective_message.reply_text(
                "Спасибо за заполнение формы согласия!\n\n"
                "Ваша информация и подпись сохранены в системе. "
                "Данные переданы в медицинский центр для обработки.\n\n"
                "Процедура завершена успешно."
            )
            
            # Очищаем данные пользователя из временного хранилища
            if user_id in user_data_storage:
                del user_data_storage[user_id]
                print(f"🗑️ Данные пользователя {user_id} очищены из памяти")
        else:
            print(f"⚠️ Неизвестное действие от веб-приложения: {data.get('action')}")
            
    except Exception as e:
        print(f"❌ Ошибка обработки данных веб-приложения: {e}")
        await update.effective_message.reply_text(
            "Произошла ошибка при обработке данных. "
            "Пожалуйста, обратитесь к администратору."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    user_id = update.effective_user.id
    if user_id in user_data_storage:
        del user_data_storage[user_id]
    
    await update.message.reply_text(
        "Операция отменена. Для начала заново отправьте /start"
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
            GENDER: [CallbackQueryHandler(get_gender, pattern="^gender_")],
            IIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_iin)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            EXAMINATION_FOR: [CallbackQueryHandler(get_examination_for, pattern="^exam_")],
            PATIENT_REPRESENTATIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_patient_representative)],
            ALLERGY: [
                CallbackQueryHandler(get_allergy, pattern="^(no_allergy|has_allergy)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_allergy_details)
            ],
            PROHIBITED_PROCEDURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_prohibited_procedures)],
            CONTACT_PERSON: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_person_flow)],
            MINOR_CONSENT: [
                CallbackQueryHandler(get_minor_consent, pattern="^minor_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_minor_consent_text)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(conv_handler)
    
    # Добавляем обработчик веб-приложения для завершения подписи
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    application.add_handler(CommandHandler('help', help_command))
    
    print(f"✅ Бот запущен! Веб-приложение: {WEB_APP_URL}")
    print("📁 Подписи будут сохраняться в папку 'signatures/'")
    print("📄 Данные пользователей сохраняются в JSON файлы")
    print("🛑 Для остановки нажмите Ctrl+C")
    
    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()