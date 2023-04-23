import logging
import os
import time
from http import HTTPStatus
from json import JSONDecodeError

import exceptions
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
    """Функция для проверки доступности переменных окружения."""
    tokens_dict = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for tokens in tokens_dict:
        if tokens not in globals():
            logger.critical('Отсутствует один, или несколько токенов')
            return False
        return True


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
            logger.error('Ошбика при запросе к API')
            raise Exception('Ошбика при запросе к API')
        return homework_status.json()
    except requests.exceptions.RequestException:
        logger.error('Эндпоинт не найден')
        raise Exception('Эндпоинт не найден')
    except JSONDecodeError:
        logger.error('Ошибка преобразования в JSON')
        raise Exception('Ошибка преобразования в JSON')
    except Exception as error:
        logger.error(f'API error: {error}')
        raise Exception(f'API error: {error}')


def check_response(response):
    """Проверяет полученный ответ на корректность."""
    logger.info("Ответ от сервера получен")
    homeworks_response = response['homeworks']
    logger.info("Список домашних работ получен")
    if 'homeworks' not in response:
        logger.error('Отсутствие ключа')
        raise KeyError('Отсутствие ключа')
    if 'current_date' not in response.keys():
        logger.error('Нет current_date')
        raise KeyError('Нет current_date')
    if type(response['homeworks']) is not list:
        logger.error('Список с домашними работами пуст')
        raise TypeError('Список с домашними работами пуст')
    return homeworks_response


def parse_status(homework):
    """Функция для проверки статуса о выполнении ДЗ."""
    if not isinstance(homework, dict):
        logger.error('Ошибка типа данных в homework')
        raise KeyError('Ошибка типа данных в homework')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise Exception(f'homework_name отсутствует {homework_name}')
    if homework_status is None:
        raise Exception(f'homework_status отсутствует {homework_status}')
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error('Ключ отсутствует в словаре')
        raise KeyError('Ключ отсутствует в словаре')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Необходимые переменные окружения отсутствуют')
        raise exceptions.TokenError('Tokens Error')
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
