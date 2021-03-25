import requests
import settings

from wechaty_puppet import get_logger
log = get_logger('mybot')


class Telegram:

    def __init__(self):
        self.url = 'http://8.210.113.182:8000/'

    def send_msg(self, text):
        log.info('start send msg to tg: {}'.format(text))
        result = requests.post(self.url, data={'text': text})
        log.info('result: {}'.format(result))
        return result


