import logging
import os
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot

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
    all_tokens_verified = True
    missing_token = []
    for name_token, value_token in tokens:
        if not value_token:
            all_tokens_verified = False
            missing_token.append(name_token)
    if not all_tokens_verified:
        logger.critical(
            f'Отсутствует обязательная переменная '
            f'окружения: {", ".join(missing_token)}'
        )
        raise KeyError('Not all tokens have been verified')


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
        if response.status_code != 200:
            code_error = (
                f'Эндпоинт {ENDPOINT} недоступен.'
                f' Код ответа API: {response.status_code}')
            logger.error(code_error)
            raise exceptions.NoAnswer200Error(code_error)
        return response.json()
    except requests.RequestException as error:
        code_error = f'Ошибка запроса: {error}'
        logger.error(code_error)
        raise exceptions.RequestError(f'Ошибка запроса: {code_error}')


def check_response(response):
    """Проверяем данные в response."""
    logging.debug('Начало проверки')
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response or 'current_date' not in response:
        raise exceptions.EmptyDictOrListError('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Homeworks не является списком')
    return homeworks


def parse_status(homework):
    """Анализируем изменение статуса."""
    try:
        status = homework['status']
    except KeyError as error:
        raise KeyError(f'Неизвестный статус: {error}')

    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        raise KeyError(f'В ответе нет ключа homework_name: {error}')

    try:
        verdict_status = HOMEWORK_VERDICTS[status]
    except KeyError as error:
        raise KeyError(f'Статус не найден: {error}')

    return (
        f'Изменился статус проверки работы "{homework_name}". {verdict_status}'
    )


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    message = None
    send_message(
        bot,
        'Привет, давай проверим твои ДЗ'
    )

    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                if response['homeworks']:
                    homework = response['homeworks'][0]
                message_new = parse_status(homework)
                if message != message_new:
                    message = message_new
                    send_message(bot, message)
                else:
                    message_new = 'Нет актуальных данных для проверки'
                    if message != message_new:
                        message = message_new
                        send_message(bot, message)

        except Exception as error:
            code_error = f'Сбой в работе: {error}'
            logger.error(code_error)
            send_message(bot, code_error)

        finally:
            logger.debug('Изменений нет, ждем 10 минут и проверяем повторно')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
