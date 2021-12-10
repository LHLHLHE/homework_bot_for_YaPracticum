import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HwStatusError, StatusCodeError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    encoding='UTF-8',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


def send_message(bot, message):
    """Отправка сообщения об изменении статуса."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('Отправлено сообщение')


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise StatusCodeError('Ошибка при запросе к API')
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
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ homework_name')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ homework_status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        raise HwStatusError('Недокументированный статус')
    elif homework_status == 'approved':
        verdict = HOMEWORK_STATUSES.get('approved')
    elif homework_status == 'reviewing':
        verdict = HOMEWORK_STATUSES.get('reviewing')
    elif homework_status == 'rejected':
        verdict = HOMEWORK_STATUSES.get('rejected')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logging.critical('Отсутствуют переменные окружения!')
    return False


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            for homework in check_response(response):
                hw_status = parse_status(homework)
                send_message(bot, hw_status)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            bot.send_message(TELEGRAM_CHAT_ID, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
