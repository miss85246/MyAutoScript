import logging
import os
from datetime import datetime

import httpx
import pytz

logging.basicConfig(level=logging.INFO, format='【%(levelname)s】%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


class SSPANELCheckin:
    def __init__(self):
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.server_key = os.environ.get('SERVER_KEY')
        self.email = os.environ.get('SSPANEL_EMAIL').split(';')
        self.passwd = os.environ.get('SSPANEL_PASSWD').split(';')
        self.domain = os.environ.get('SSPANEL_DOMAIN').split(';')
        self.results = []
        self.headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'}
        if len(self.email) != len(self.passwd):
            print('邮箱和密码数量不一致，请修正后再进行操作，分割符是英文的分号 “;”')
            exit(1)

    def checkin(self, domain, email, passwd):
        try:
            with httpx.Client(headers=self.headers) as client:
                data = {'email': email, 'passwd': passwd}
                resp = client.post(f'{domain}/auth/login', data=data).json()
                logger.info(resp['msg'])
                resp = client.post(f'{domain}/user/checkin').json()
                logger.info(resp['msg'])
                self.results.append((domain, email, resp['msg']))
        except Exception as e:
            logger.error(f"未知错误：「{e}」")
            self.results.append((domain, email, '签到失败'))

    def send_notice(self):
        params = {
            "title": "SSPANEL签到结果通知",
            "desp" : "\n".join(
                [
                    f"{datetime.now(self.timezone).strftime('%Y-%m-%d')} 您的账号进行了签到，签到结果如下：\n",
                    "===============================================================================\n",
                    '###############################################################################\n'.join(
                        [f"{domain:<20}&nbsp;&nbsp;&nbsp;&nbsp;{email:<12}&nbsp;&nbsp;&nbsp;&nbsp;{msg:<45} \n" for domain, email, msg in self.results]
                    ),
                    "===============================================================================\n",
                ]
            )
        }
        httpx.post(f'https://sctapi.ftqq.com/{self.server_key}.send', params=params)

    def main(self):
        for domain in self.domain:
            for email, passwd in zip(self.email, self.passwd):
                self.headers['origin'] = f"{domain}"
                self.checkin(domain, email, passwd)
        self.send_notice()


if __name__ == '__main__':
    ssp = SSPANELCheckin()
    ssp.checkin()
