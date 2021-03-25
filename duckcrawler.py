import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class DuckCrawler:

    def fetch_bihu(self, content_id):
        url = 'https://gw.bihu.com/api/content/shortContent/{}'.format(content_id)
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
            'uuid': '72d3f5b38bed9d44845b91112081e507',
        }
        res = requests.get(url, headers=headers)
        data = res.json()
        if data['code'] == 1:
            data = data['data']
            data['post_date'] = datetime.fromtimestamp(data['createTS'] // 1000)
            if 'imageUrlList' in data:
                data['img_url'] = data['imageUrlList']
            return data['data']
        else:
            return None

    def fetch_chainnode(self, content_id):
        url = 'https://m.chainnode.com/post/{}'.format(content_id)
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        }
        res = requests.get(url, headers=headers)
        try:
            soup = BeautifulSoup(res.text, 'html.parser')
            script_str = str(soup.find('script', text=re.compile(r'pubDate', re.MULTILINE | re.DOTALL)))
            script_data = json.loads(re.sub(r'<.+?>', '', script_str))
            content = soup.find('meta', attrs={'name': 'description'}).get('content')
            data = {
                'post_date': datetime.strptime(script_data['pubDate'], '%Y-%m-%dT%H:%M:%S'),
                'content': '{}\n{}'.format(script_data['title'], content),
            }
            if 'images' in data and data['images']:
                data['img_url'] = data['images'][0]
            return data
        except Exception as e:
            log.exception(e)
            return None
