import requests

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
            return data['data']
        else:
            return None
