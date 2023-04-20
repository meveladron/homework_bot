from http import HTTPStatus
import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

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

MESSAGE = 'Ошбика при запросе к API'
NOT_HOMEWORKS = 'Нет ключа homeworks'
HOMEWORK_LIST = 'Список с домашками пуст'
HOMEWORK_STATUS = 'Ключа нет в словаре'
NOT_CURRENT_DATE = 'Нет current_date'
NOT_HOMEWORK_LIST = 'Ошибка типа данных в homework'
NOT_KEY = 'Отсутствует ключ'
STATUS = 'Отсутствует статус в homeworks'
TYPE_HOMEWORK_LIST = 'Ошибка типа данных в homework_list'

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


class TokenError(Exception):
    """Ошибка токенов."""


class HomeworksKeyError(Exception):
    """В ответе API домашки нет ключа homeworks."""


class MissedKeyException(Exception):
    """."""


class WrongDataFormat(Exception):
    """."""


def check_tokens():
    """Функция для проверки доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Функция для отправки сообщения в чат Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'Сообщение в чат отправлено: {message}'
        )
        return True
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение в чат не отправлено: {telegram_error}'
        )


def get_api_answer(timestamp):
    """Функция для запроса к эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_status.status_code != HTTPStatus.OK:
            logger.error(MESSAGE)
            raise Exception(MESSAGE)
        return homework_status.json()
    except Exception as Error:
        logger.error(f'Ошибка {Error} при запросе к API')
        raise Exception(f'Ошибка {Error}')


def check_response(response):
    """Функция для проверки ответа API на корректность."""
    if type(response) is not dict:
        logger.error(STATUS)
        raise TypeError(STATUS)
    if 'homeworks' not in response.keys():
        logger.error(NOT_KEY)
        raise KeyError(NOT_KEY)
    if 'current_date' not in response.keys():
        logger.error(NOT_CURRENT_DATE)
        raise KeyError(NOT_CURRENT_DATE)
    if type(response['homeworks']) is not list:
        logger.error(HOMEWORK_LIST)
        raise TypeError(HOMEWORK_LIST)
    return response['homeworks'][0]


def parse_status(homework):
    """Функция для проверки статуса о выполнении ДЗ."""
    if not isinstance(homework, dict):
        logger.error(NOT_HOMEWORK_LIST)
        raise KeyError(NOT_HOMEWORK_LIST)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise Exception(f'homework_name отсутствует {homework_name}')
    if homework_status is None:
        raise Exception(f'homework_status отсутствует {homework_status}')
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error(HOMEWORK_STATUS)
        raise KeyError(HOMEWORK_STATUS)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствие обязательных переменных окружения')
        raise TokenError('Ошибка токенов')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    previous_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check = check_response(response)
            message = parse_status(check)
            if last_message != message:
                last_message = message
                send_message(bot, last_message)
                time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != previous_message and send_message(
                    bot, message):
                previous_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
