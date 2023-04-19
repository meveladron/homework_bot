import logging
import os
import sys
import time
from http import HTTPStatus

import exceptions
import requests
import telegram
from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler_recorder = logging.FileHandler('my_log.log')
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
)
handler.setFormatter(formatter)
handler_recorder.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(handler_recorder)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('Началась отправка')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
    except exceptions.TelegramError as error:
        raise exceptions.TelegramError(
            f'Не удалось отправить сообщение {error}')
    else:
        logging.info(f'Сообщение отправлено {message}')


def get_api_answer(current_timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    parameters = {'from_date': timestamp}
    auth = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    logger.info('Отправка запроса')
    try:
        response = requests.get(ENDPOINT, headers=auth, params=parameters)
    except Exception as error:
        raise exceptions.ErrorServer('Ошибка при запросе к эндпоинту: '
                                     f'{error}')
    if response.status_code != HTTPStatus.OK:
        raise exceptions.HTTPStatusError('API не вернула statuscode 200')
    logger.info('Ответ от API успешно получен')
    return response.json()


def check_response(response):
    """проверяет ответ API на корректность."""
    if not isinstance(response['homeworks'], list):
        raise exceptions.UncorrectDataAPI('под ключом `homeworks` ответы '
                                          'приходят не в виде списка')
    if 'homeworks' not in response.keys():
        raise exceptions.UncorrectDataAPI(
            'ответ от API не содержит '
            'ключа `homeworks`'
        )
    return response['homeworks']


def parse_status(homework):
    """Извлечение статуса работы."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    verdict = HOMEWORK_VERDICTS[homework_status]
    if not verdict:
        message_verdict = "Такого статуса нет в словаре"
        raise KeyError(message_verdict)
    if homework_status not in HOMEWORK_VERDICTS:
        message_homework_status = "Такого статуса не существует"
        raise KeyError(message_homework_status)
    if "homework_name" not in homework:
        message_homework_name = "Такого имени не существует"
        raise KeyError(message_homework_name)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет наличие переменных в локальном хранилище."""
    token_list = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    return token_list


def main():
    """Основная логика работы бота."""
    logger.info("Starting")
    if not check_tokens():
        logger.error('Отсутствуют обязательные переменные')
        sys.exit(
            'Отсутствие обязательных переменных '
            'окружения во время запуска бота'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    current_timestamp = int(time.time())
    status = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            response_list = check_response(response)
            current_timestamp = response.get('current_date', current_timestamp)
            if len(response_list) > 0:
                homework = response_list[0]
                current_status = parse_status(homework)
                if current_status != status:
                    status = current_status
                    message = current_status
                    send_message(bot, message)
            else:
                logger.debug('Отсутствие новых статусов')
        except Exception as error:
            message = f'Программа работает некорректно: {error}'
            send_message(bot, message)
            logger.exception('Сообщение в telegram не отправлено')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
