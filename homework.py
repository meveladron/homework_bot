import logging
import os
import sys
from http import HTTPStatus
from json import JSONDecodeError
from logging import StreamHandler
from time import sleep, time

import exceptions
import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    level=logging.DEBUG)

handler = StreamHandler(sys.stdout)
logger = logging.getLogger(__name__)
logger.addHandler(handler)

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
old_message = ''


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    global old_message
    try:
        if old_message != message:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            old_message = message
            logger.info(f'Сообщение успешно отправлено: {message}')
    except TelegramError as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.ConnectionError as errc:
        raise Exception(f'Ошибка соединения: {errc}')
    except requests.exceptions.Timeout as errt:
        raise Exception(f'Таймаут при запросе: {errt}')
    except requests.exceptions.RequestException as err:
        raise Exception(f'Ошибка при запросе API: {err}')
    if response.status_code != HTTPStatus.OK:
        raise Exception(f'Ошибка при запросе API: {response.status_code}')

    try:
        response_json = response.json()
        return response_json
    except JSONDecodeError as errj:
        raise Exception(f'Ошибка при возврате JSON: {errj}')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка типа данных: в ответе API должен быть словарь')
    if 'current_date' not in response:
        raise Exception('В ответе API отсутствует ключ current_date')
    if 'homeworks' not in response:
        raise Exception('В ответе API отсутствует ключ homeworks')
    hw_list = response.get('homeworks', [])
    if hw_list is None:
        raise exceptions.CheckResponseException('Список домашних заданий пуст')
    if len(hw_list) == 0:
        raise exceptions.CheckResponseException(
            'Домашнего задания нет за данный промежуток времени')
    if not isinstance(hw_list, list):
        raise TypeError('Ответ API не является списком')
    return hw_list


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('Ошибка, отсутствует статус домашней работы')
    if homework_name is None:
        raise KeyError('Ошибка, пустое значение homework_name')

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if verdict is None:
        raise KeyError('Ошибка, неизвестное значение status')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if (
        PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
        or TELEGRAM_CHAT_ID is None
    ):
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Ошибка, отсутствуют переменные окружения')
        exit()

    current_timestamp = int(time())
    previous_status = None
    bot = Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            current_timestamp = response.get('current_date', [])
            status = homeworks[0].get('status')
            if status != previous_status:
                previous_status = status
                send_message(bot, parse_status(homeworks[0]))
        except exceptions.CheckResponseException as response_status:
            logger.info(f'Обновление статуса: {response_status}')
        except Exception as error:
            msg_err = f'Сбой в работе программы: {error}'
            logger.error(msg_err)
            send_message(bot, msg_err)
        else:
            logger.debug('Работа программы без замечаний')
        finally:
            sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
