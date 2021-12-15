import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import StatusCodeError

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

SEND_MESSAGE_INFO = 'Отправлено сообщение:'
API_ANSWER_ERROR = 'Ошибка при запросе к API:'
UNKNOWN_STATUS_ERROR = 'Неизвестный статус:'


def send_message(bot, message):
    """Отправка сообщения об изменении статуса."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info(f'{SEND_MESSAGE_INFO} "{message}"')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise ConnectionError(f'{API_ANSWER_ERROR} {error}')
    if response.status_code != 200:
        raise StatusCodeError(
            f'{API_ANSWER_ERROR} {response.status_code}, '
            f'{ENDPOINT}, {HEADERS}, {params}')
    return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if type(response) is not dict:
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ homeworks')
    if type(response['homeworks']) is not list:
        raise TypeError(
            'Под ключом `homeworks` домашки приходят не в виде списка')
    return response.get('homeworks')


def parse_status(homework):
    """Извлечение из информации о домашней работе статуса этой работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in VERDICTS.keys():
        raise KeyError(f'{UNKNOWN_STATUS_ERROR} {homework_status}')
    return (
        f'Изменился статус проверки работы "{homework_name}".'
        f' {VERDICTS.get(homework_status)}')


def check_tokens():
    """Проверка наличия токенов."""
    tokens = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    for name in tokens:
        if globals()[name] is None:
            logging.critical(f'Токен {name} не найден!')
            return False
        return True


def main():
    """Основная логика работы бота."""
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homeworks = check_response(response)
                if homeworks:
                    send_message(bot, parse_status(homeworks[0]))
                if 'current_date' in response:
                    current_timestamp = response['current_date']
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.exception(message)
                try:
                    bot.send_message(TELEGRAM_CHAT_ID, message)
                except Exception as error:
                    logging.exception(error)
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
