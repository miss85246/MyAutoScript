import logging
import os
from datetime import datetime
from hashlib import md5
from time import time

import httpx
import pytz

logging.basicConfig(level=logging.INFO, format='【%(levelname)s】%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)


class BaiduTieBa:
    def __init__(self):
        self.bduss_list = os.environ.get('BAIDU_BDUSS', '').split('#')
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.server_key = os.environ.get('SERVER_KEY')
        self.results = []
        self.client = None
        self.tbs = None
        self.bduss = None
        self.need_checkin_tieba = []
        self.headers = {
            'Host'      : 'tieba.baidu.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        }

    @staticmethod
    def _data_encode(data: dict):
        string = "".join([f"{key}={value}" for key, value in sorted(data.items(), key=lambda x: x[0])])
        data.update({'sign': md5((string + 'tiebaclient!!!').encode()).hexdigest().upper()})
        return data

    def get_account_tbs(self):
        try:
            tbs = self.client.get("http://tieba.baidu.com/dc/common/tbs").json()['tbs']
            self.tbs = tbs
        except Exception as e:
            logger.error(f"获取账号tbs出错，错误原因：{e}")

    def get_likely_forums(self, bduss, page_no: int = 1):
        try:
            source_data = {
                'BDUSS'          : bduss,
                '_client_type'   : '2',
                '_client_id'     : 'wappc_1534235498291_488',
                '_client_version': '9.7.8.0',
                '_phone_imei'    : '000000000000000',
                'from'           : '1008621y',
                'page_no'        : str(page_no),
                'page_size'      : '200',
                'model'          : 'MI+5',
                'net_type'       : '1',
                'timestamp'      : str(int(time())),
                'vcode_tag'      : '11',
            }
            send_data = self._data_encode(source_data)
            resp = self.client.post("https://c.tieba.baidu.com/c/f/forum/like", data=send_data).json()
            forums = resp.get('forum_list', {})
            non_gconforum, gconforum = forums.get('non-gconforum', []), forums.get('gconforum', [])
            self.need_checkin_tieba.extend(non_gconforum)
            self.need_checkin_tieba.extend(gconforum)
            if int(resp.get('has_more', 0)):
                self.get_likely_forums(bduss, page_no + 1)
        except Exception as e:
            logger.error(f"获取贴吧出错，错误原因：{e}")

    def checkin(self, bduss, forum, success_count, failed_count):
        try:
            source_data = {
                'BDUSS'          : bduss,
                'fid'            : forum['id'],
                'kw'             : forum['name'],
                'tbs'            : self.tbs,
                'timestamp'      : str(int(time())),
                '_client_type'   : '2',
                '_client_version': '9.7.8.0',
                '_phone_imei'    : '000000000000000',
                'model'          : 'MI+5',
                "net_type"       : "1",
            }
            send_data = self._data_encode(source_data)
            resp = self.client.post("https://c.tieba.baidu.com/c/c/forum/sign", data=send_data).json()
            if resp.get('error_code') in ('160002', '0'):
                success_count += 1
            else:
                failed_count += 1
            return success_count, failed_count
        except Exception as e:
            logger.error(f"签到贴吧 {forum['name']} 出错，错误原因：{e}")
            return success_count, failed_count + 1

    def send_notice(self):
        params = {
            "title": "百度贴吧签到结果通知",
            "desp" : "\n".join(
                [
                    f"{datetime.now(self.timezone).strftime('%Y-%m-%d')} 您的账号进行了签到，签到结果如下：\n",
                    "===============================================================================\n",
                    '###############################################################################\n'.join(
                        [f"{account:<20}&nbsp;&nbsp;&nbsp;&nbsp;{success:<12}&nbsp;&nbsp;&nbsp;&nbsp;{failed:<45} \n" for account, success, failed in
                         self.results]
                    ),
                    "===============================================================================\n",
                ]
            )
        }
        httpx.post(f'https://sctapi.ftqq.com/{self.server_key}.send', params=params)

    def main(self):
        for index, bduss in enumerate(self.bduss_list, start=1):
            success, failed, self.need_checkin_tieba = 0, 0, []
            self.headers.update({'Cookie': f"BDUSS={bduss}"})
            self.client = httpx.Client(headers=self.headers)
            logger.info("开始获取获取贴吧")
            self.get_account_tbs()
            self.get_likely_forums(bduss)
            logger.info(f"获取贴吧成功，共获取到 {len(self.need_checkin_tieba)} 个贴吧")
            for forum in self.need_checkin_tieba:
                success, failed = self.checkin(bduss, forum, success, failed)
            self.results.append((f'第 {index} 个账户', f'签到成功 {success} 个，签到失败 {failed} 个'))
            self.send_notice()


if __name__ == '__main__':
    bd = BaiduTieBa()
    bd.main()
