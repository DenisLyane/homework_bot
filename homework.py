import logging
import os
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from http import HTTPStatus

import exceptions

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


def check_tokens():
    """Проверка токенов."""
    tokens = (
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN),
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID)
    )
    missing_token = []
    for name_token, value_token in tokens:
        if value_token is None:
            missing_token.append(name_token)
    if missing_token:
        code_error = ', '.join(missing_token)
        raise KeyError(f'Не установлены следующие токены:'
                       f'{code_error}')
    return True


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'Сообщение в Telegram отправлено: {message}')
    except Exception as error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {error}')


def get_api_answer(timestamp):
    """Получение данных с API YndxPrct."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise exceptions.RequestError(f'Ошибка запроса: {error}')
    if response.status_code != HTTPStatus.OK:
        code_error = (
            f'Эндпоинт {ENDPOINT} недоступен.'
            f' Код ответа API: {response.status_code}')
        raise exceptions.NoAnswer200Error(code_error)
    return response.json()


def check_response(response):
    """Проверяем данные в response."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response:
        raise exceptions.EmptyDictOrListError('Пустой ответ от API')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Homeworks не является списком')
    return True


def parse_status(homework):
    """Анализируем изменение статуса."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('Неизвестный статус')
    if homework_name is None:
        raise KeyError('В ответе нет ключа homework_name')

    if homework_status in HOMEWORK_VERDICTS:
        verdict_status = HOMEWORK_VERDICTS[homework_status]
        return (
            f'Изменился статус проверки работы '
            f'"{homework_name}". {verdict_status}'
        )
    raise KeyError('Статус не найден')


def main():
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = 0
    message = None
    try:
        check_tokens()
    except Exception as error:
        logger.critical(error)
        raise SystemExit

    send_message(
        bot,
        'Привет, давай проверим твои ДЗ'
    )

    while True:
        try:
            response = get_api_answer(timestamp)
            if message != check_response(response):
                send_message(bot, parse_status(response['homeworks'][0]))
                message = check_response(response)
                continue

        except Exception as error:
            code_error = f'Сбой в работе: {error}'
            logger.error(code_error)
            send_message(bot, code_error)

        finally:
            logger.debug('Изменений нет, ждем 10 минут и проверяем повторно')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
