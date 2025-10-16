# Telegram Bot for Railway

Telegram bot that collects user data and signature through a web application.

## Features

- Collects user information (ФИО, дата рождения, телефон, ИИН)
- Signature collection via web application
- Direct integration with n8n webhook
- Sends success notifications to users

## Deployment

This bot is configured to run on Railway.

### Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token

## Usage

1. Start conversation with `/start`
2. Fill in personal information
3. Draw signature in web application
4. Data is sent to n8n webhook automatically
5. Receive success notification in Telegram

## Web Application

The signature web app is hosted separately at: https://railway-web-page-production.up.railway.app