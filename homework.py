import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (
    ResponseError,
    SendMessageError,
    StatusCodeError,
    TokenError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

SEND_MESSAGE_INFO = 'Отправлено сообщение: "{}"'
API_ANSWER_ERROR = ('Ошибка подключения к API: {}. '
                    'endpoint: {}, headers: {}, params: {}')
RESPONSE_ERROR = ('Отказ от обслуживания: {}. '
                  'status_code: {}, endpoint:{}, headers: {}, params: {}')
STATUS_CODE_ERROR = ('Ошибка при запросе к API: '
                     'status_code: {}, endpoint: {}, headers: {}, params: {}')
UNKNOWN_STATUS_ERROR = 'Неизвестный статус: {}'
CHANGED_STATUS = 'Изменился статус проверки работы "{}". {}'
RESPONSE_NOT_DICT = 'Ответ API не является словарем'
HOMEWORKS_NOT_IN_RESPONSE = 'Отсутствует ключ homeworks'
HOMEWORKS_NOT_LIST = 'Под ключом `homeworks` домашки приходят не в виде списка'
TOKEN_NOT_FOUND = 'Токен {} не найден!'
ERROR_MESSAGE = 'Сбой в работе программы: {}'
HOMEWORK_NAME_NOT_FOUND = 'Не найден ключ `homeworks`!'
SEND_MESSAGE_ERROR = 'Ошибка при отправке сообщения: {}'
TOKEN_ERROR = 'Ошибка в токенах!'


def send_message(bot, message):
    """Отправка сообщения об изменении статуса."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info(SEND_MESSAGE_INFO.format(message))


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except ConnectionError as error:
        raise ConnectionError(
            API_ANSWER_ERROR.format(error, ENDPOINT, HEADERS, params))
    response_json = response.json()
    status_code = response.status_code
    if status_code != 200:
        raise StatusCodeError(
            STATUS_CODE_ERROR.format(
                status_code,
                ENDPOINT,
                HEADERS,
                params))
    if 'error' in response_json:
        raise ResponseError(
            RESPONSE_ERROR.format(
                response_json['error'],
                status_code,
                ENDPOINT,
                HEADERS,
                params))
    if 'code' in response_json:
        raise ResponseError(
            RESPONSE_ERROR.format(
                response_json['code'],
                status_code,
                ENDPOINT,
                HEADERS,
                params))
    return response_json


def check_response(response):
    """Проверка ответа API на корректность."""
    if type(response) is not dict:
        raise TypeError(RESPONSE_NOT_DICT)
    if 'homeworks' not in response:
        raise KeyError(HOMEWORKS_NOT_IN_RESPONSE)
    if type(response['homeworks']) is not list:
        raise TypeError(HOMEWORKS_NOT_LIST)
    return response.get('homeworks')


def parse_status(homework):
    """Извлечение из информации о домашней работе статуса этой работы."""
    status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError(HOMEWORK_NAME_NOT_FOUND)
    if status not in VERDICTS:
        raise ValueError(UNKNOWN_STATUS_ERROR.format(status))
    return (CHANGED_STATUS.format(
        homework['homework_name'],
        VERDICTS.get(status)))


def check_tokens():
    """Проверка наличия токенов."""
    for name in TOKENS:
        if globals()[name] is None:
            logging.critical(TOKEN_NOT_FOUND.format(name))
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise TokenError(TOKEN_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = ERROR_MESSAGE.format(error)
            logging.exception(message)
            try:
                bot.send_message(TELEGRAM_CHAT_ID, message)
            except Exception as error:
                raise SendMessageError(SEND_MESSAGE_ERROR.format(error))
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(__file__ + '.log', encoding='UTF-8')],
        format=(
            '%(asctime)s, %(levelname)s, %(funcName)s, %(lineno)d, %(message)s'
        ))
    main()
