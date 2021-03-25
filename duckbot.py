import asyncio
from wechaty import Wechaty, Message, UrlLink, Room, Contact
import requests
import time
from wechaty_puppet import get_logger, FileBox
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import os
import re
import cv2
import json
import random
import base64
import threading
import concurrent.futures

from selenium import webdriver
from io import BytesIO
from PIL import Image, ImageChops
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

log = get_logger('mybot')

digit62 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

class DuckBot(Wechaty):

    my_contact_id = 'wxid_teg271qn16q622'
    my_contact_name = '可达机器鸭'
    god_contact_id = 'wxid_lj5i9wj91mnu22'
    god_last_msg_id = ''

    detector = cv2.QRCodeDetector()
    ad_qa_dict = {
        'Kadena的代币叫什么？': 'KDA',
        'Kadena的区块链编程语言是什么？': 'Pact',
        'Kadena目前有多少条链？': '20',
        '本群的项目英文名是什么？': 'Kadena',
    }

    def set_driver(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--headless")

    def set_db(self, db):
        self.db = db

    def set_crawler(self, crawler):
        self.crawler = crawler

    def set_telegram(self, telegram):
        self.telegram = telegram

    async def on_message(self, msg: Message):

        # 加载消息发送者
        talker = msg.talker()
        await talker.ready()

        # 忽略自己发的消息
        if talker.contact_id == self.my_contact_id:
            return

        # 加载聊天室信息
        room = msg.room()
        room_topic = None
        if room:
            await room.ready()
            room_topic = await room.topic()

        # 基本信息
        msg_text = msg.text()
        msg_text_inline = msg.text().replace('\n', '')
        msg_type = msg.message_type()
        msg_id = msg.message_id
        if msg_type == 6:
            log.info('Received text, msg_type = {}, id = {}'.format(msg_type, msg_id))
        else:
            log.info('Received text = {}, msg_type = {}, id = {}'.format(msg_text, msg_type, msg_id))

        # 保存聊天记录
        insert_data = {
            'contact_id': talker.contact_id,
            'contact_name': talker.name,
            'room_id': room.room_id if room else None,
            'room_name': room_topic,
            'msg_id': msg_id,
            'msg_text': msg_text[:20],
            'created_at': datetime.now()
        }
        keys = ','.join(['`{}`'.format(str(v)) for v in insert_data.keys()])
        values = ','.join(['\'{}\''.format(str(v)) for v in insert_data.values()])
        sql = 'INSERT INTO {table}({keys}) VALUES({values})'.format(table='msg_records', keys=keys, values=values)
        try:
            self.db.cursor.execute(sql)
            self.db.db.commit()
        except Exception as e:
            log.error(e)
            self.db.db.rollback()

        # 鉴定是否为广告
        if room and not re.match(r'.*(kda|kadena|可达).*', msg_text_inline.lower()):
            is_ad = False
            if msg_type == 4:
                pass
            elif msg_type == 5:
                # 识别是否有二维码
                img = await msg.to_file_box()
                log.info('get img {}'.format(img.name))
                img_path = './images/{}'.format(img.name)
                img_file = await img.to_file(img_path)
                log.info('get img stored')
                img = cv2.imread(img_path)
                data, bbox, straight_qrcode = self.detector.detectAndDecode(img)
                log.info('qrcode results: {}, {}, {}'.format(data, bbox, straight_qrcode))
                if bbox is not None:
                    log.info('ad detected qr_code')
                    is_ad = True
                os.remove(img_path)
            elif msg_type == 6:
                if len(msg_text) >= 50 and re.match(r'.*(http|空投|撸).*', msg_text) and not re.match(r'.*bihu\.com.*', msg_text):
                    log.info('ad detected text')
                    is_ad = True

            if is_ad:
                sql = """SELECT count(*) as msg_cnt FROM {} where contact_id = '{}'""".format('msg_records', talker.contact_id)
                self.db.cursor.execute(sql)
                if list(self.db.cursor.fetchall())[0]['msg_cnt'] < 10:
                    q_list = list(self.ad_qa_dict.keys())
                    question = q_list[random.randrange(0, len(q_list))]
                    threading.Thread(target=self.kick_member, args=(talker, room, question)).start()
                    reply = '@{}\n你有打广告的嫌疑哦，请在15秒内回答以下问题，否则给你抱出去~~~\n{}'.format(talker.name, question)
                    await room.say(reply, mention_ids=[talker.contact_id])
                    return

        # GOD的指令
        if talker.contact_id == self.god_contact_id and 'c/' in msg_text:
            if 'c/new' in msg_text:
                if '上一条' in msg_text:
                    sql = """SELECT msg_id FROM {} where contact_id = '{}' order by created_at desc""".format('msg_records', self.god_contact_id)
                    self.db.cursor.execute(sql)
                    refer_msg_id = list(self.db.cursor.fetchall())[1]['msg_id']
                    title = msg_text
                else:
                    root = ET.fromstring(msg_text)
                    refer_msg_id = root.find('.//refermsg//svrid').text
                    title = root.find('.//title').text
                keyword = re.findall('#.+#', title)[0].replace('#', '')
                log.info('title = {}, keyword = {}'.format(title, keyword))
                insert_data = {
                    'keyword': keyword,
                    'msg_id': refer_msg_id,
                    'created_at': datetime.now()
                }
                keys = ','.join(['`{}`'.format(str(v)) for v in insert_data.keys()])
                values = ','.join(['\'{}\''.format(str(v)) for v in insert_data.values()])
                sql = 'INSERT INTO {table}({keys}) VALUES({values})'.format(table='materials', keys=keys, values=values)
                try:
                    self.db.cursor.execute(sql)
                    self.db.db.commit()
                    log.info('INSERT succesfully: {}'.format(sql))
                except Exception as e:
                    log.error(e)
                    self.db.db.rollback()

                reply = '指令已储存，关键词：{}'.format(keyword)
                await msg.say(reply)

            elif 'c/list' in msg_text:
                sql = """SELECT keyword FROM {} group by keyword""".format('materials')
                self.db.cursor.execute(sql)
                reply = '现有指令'
                for row in self.db.cursor.fetchall():
                    reply += '\n' + row['keyword']

                await msg.say(reply)

            elif 'c/show' in msg_text:
                keyword = re.findall('#.+#', msg_text)[0].replace('#', '')
                await self.send_msg_with_keyword(keyword, contact=talker, room=room)

            elif 'c/active' in msg_text:
                today = datetime.now()
                start_dt = datetime(today.year, today.month, today.day)
                sql = """SELECT contact_id, count(*) as msg_cnt
                        FROM {} where room_id = '{}' and created_at >= '{}'
                        group by contact_id""".format('msg_records', room.room_id, start_dt)
                self.db.cursor.execute(sql)
                records = [row['contact_id'] for row in self.db.cursor.fetchall()]
                member_list = await room.member_list()
                reply = '今日群内未发言成员：'
                for member in member_list:
                    if member.contact_id != self.my_contact_id and member.contact_id not in records:
                        reply += '\n' + member.name

                topic = await room.topic()
                if '星火' in topic:
                    reply += '\n如果没法保持每天活跃，会被移出此群哦~'
                await msg.say(reply)

            elif 'c/fixroomname' in msg_text:
                log.info('to fix room name')
                sql = """SELECT * FROM {} WHERE room_id is not null and room_name = ''""".format('msg_records')
                self.db.cursor.execute(sql)
                for row in self.db.cursor.fetchall():
                    to_fix_room = self.Room(room_id=row['room_id'])
                    await to_fix_room.ready()
                    to_fix_room_name = await to_fix_room.topic()

                    sql = """UPDATE {} SET room_name = '{}' where id = {}""".format('msg_records', to_fix_room_name, row['id'])
                    try:
                        self.db.cursor.execute(sql)
                        self.db.db.commit()
                        log.info('update succesfully: {}'.format(sql))
                    except Exception as e:
                        log.error(e)
                        self.db.db.rollback()

                log.info('finished')

            elif 'c/kdashill_to_tg' in msg_text:
                log.info('to send telegram')
                sql = """SELECT * FROM {} WHERE has_sent_tg is null""".format('kdashill_records')
                self.db.cursor.execute(sql)
                for row in self.db.cursor.fetchall():
                    url = 'https://m.bihu.com/shortcontent/{}'.format(row['content_id'])
                    data = None
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self.telegram.send_msg, url)
                        data = future.result()

                    log.info('get res: {}'.format(data))
                    if data:
                        sql = """UPDATE {} SET has_sent_tg = {} where content_id = '{}'""".format('kdashill_records', 1, row['content_id'])
                        try:
                            self.db.cursor.execute(sql)
                            self.db.db.commit()
                            log.info('update succesfully: {}'.format(sql))
                        except Exception as e:
                            log.error(e)
                        self.db.db.rollback()

                    time.sleep(1)
                    break

            return


        # 推荐活动
        if room and re.match(r'.*[bihu|chainnode]\.com.*', msg_text_inline):
            content_id = None
            match_results = re.search(r'(?<=bihu\.com/s/)[0-9A-Za-z]{1,}', msg_text)
            if match_results:
                key = match_results[0]
                x = 0
                for y in key:
                    k = digit62.find(y)
                    if k >= 0:
                       x = x * 62 + k
                content_id = str(x)
                platform = 'bihu'
                log.info('transfer {} to {}'.format(key, content_id))
            elif 'bihu' in msg_text:
                match_results = re.search(r'(?<=bihu\.com/shortcontent/)\d{1,}', msg_text_inline.lower())
                content_id = match_results[0]
                platform = 'bihu'
            elif 'chainnode' in msg_text:
                match_results = re.search(r'(?<=chainnode\.com/post/)\d{1,}', msg_text_inline.lower())
                content_id = match_results[0]
                platform = 'chainnode'
            else:
                log.info('not find pattern')

            if content_id:
                log.info('get content id = {}'.format(content_id))
                data = None
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    if platform == 'bihu':
                        future = executor.submit(self.crawler.fetch_bihu, content_id)
                    else:
                        future = executor.submit(self.crawler.fetch_chainnode, content_id)
                    data = future.result()

                log.info('fetched data = {}'.format(data))
                if data:
                    content_inline = data['content'].replace('\n', '')
                    post_date = data['post_date']
                    if not re.match(r'.*(kda|kadena|可达).*', content_inline.lower()):
                        reply = '未发现Kadena相关信息哦~'
                        reply = reply + ' @{}'.format(talker.name)
                        await room.say(reply, mention_ids=[talker.contact_id])
                        return
                    elif post_date < datetime(2021, 3, 26) or post_date >= datetime(2021, 4, 2):
                        reply = '文章发布时间不在活动范围内，不能算入哦~'
                        reply = reply + ' @{}'.format(talker.name)
                        await room.say(reply, mention_ids=[talker.contact_id])
                        return

                    # 展示
                    sql = """SELECT * FROM {} where phase = 1 and platform = '{}' and content_id = '{}'""".format('kdashill_records', platform, content_id)
                    self.db.cursor.execute(sql)
                    results = list(self.db.cursor.fetchall())
                    if len(results):
                        # 处理重复
                        is_duplicate = True
                        ww_id = results[0]['id']
                        from_room = self.Room(room_id=results[0]['room_id'])
                        await from_room.ready()
                        from_room_name = await from_room.topic()
                        room_name_str = '「{}」\n'.format(from_room_name.replace('Kadena', ''))
                        from_contact = self.Contact(contact_id=results[0]['contact_id'])
                        await from_contact.ready()
                        from_contact_name = from_contact.name
                    else:
                        is_duplicate = False
                        sql = """SELECT max(id) as max_id FROM {} """.format('kdashill_records')
                        self.db.cursor.execute(sql)
                        max_id = list(self.db.cursor.fetchall())[0]['max_id']
                        ww_id = max_id + 1
                        room_name_str = '「{}」\n'.format(room_topic.replace('Kadena', ''))
                        from_contact_name = talker.name

                    reply_title = '可达秀.{:02} @ {}'.format(ww_id, from_contact_name)
                    if platform == 'bihu':
                        reply_url = 'https://m.bihu.com/shortcontent/{}'.format(content_id)
                        score = 1
                        if 'img_url' in data:
                            prefix = 'https://oss-cdn1.bihu-static.com/'
                            reply_thumbnail = prefix + data['img_url']
                        else:
                            reply_thumbnail = 'https://m.bihu.com/static/img/pic300.jpg'
                    else:
                        score = 2
                        reply_url = 'https://www.chainnode.com/post/{}'.format(content_id)
                        if 'img_url' in data:
                            reply_thumbnail = data['img_url']
                        else:
                            reply_thumbnail = 'https://webcdn.chainnode.com/mobile-1.3.15/img/ChainNode.4e5601a.svg'
                    reply_description = room_name_str + data['content'][:60]
                    log.info('to create url_link: {},{},{},{}'.format(reply_url, reply_title, reply_thumbnail, reply_description))
                    reply_link = UrlLink.create(reply_url, reply_title, reply_thumbnail, reply_description)
                    log.info('url created')

                    # 查重
                    if is_duplicate:
                        reply = '文章已有录入哦~'
                        reply = reply + ' @{}'.format(talker.name)
                        await room.say(reply, mention_ids=[talker.contact_id])

                        return

                    # 记分
                    insert_data = {
                        'phase': 2,
                        'platform': platform,
                        'content_id': content_id,
                        'contact_id': talker.contact_id,
                        'contact_name': talker.name,
                        'room_id': room.room_id,
                        'created_at': datetime.now(),
                        'score': score,
                    }
                    keys = ','.join(['`{}`'.format(str(v)) for v in insert_data.keys()])
                    values = ','.join(['\'{}\''.format(str(v)) for v in insert_data.values()])
                    sql = 'INSERT INTO {table}({keys}) VALUES({values})'.format(table='kdashill_records', keys=keys, values=values)
                    try:
                        self.db.cursor.execute(sql)
                        self.db.db.commit()
                        log.info('INSERT succesfully: {}'.format(sql))
                    except Exception as e:
                        log.error(e)
                        self.db.db.rollback()

                    # 报积分
                    sql = """SELECT contact_id, sum(score) as score FROM {} where phase = 2 group by contact_id order by score desc""".format('kdashill_records')
                    self.db.cursor.execute(sql)
                    rank = 0
                    for row in self.db.cursor.fetchall():
                        rank += 1
                        if row['contact_id'] == talker.contact_id:
                            reply = '感谢参加可达秀 [KDA-Show] 活动！🍻\n'
                            reply += '您当前积分为{}，排名为{}'.format(row['score'], rank)
                            break

                    reply = reply + ' @{}'.format(talker.name)
                    await room.say(reply, mention_ids=[talker.contact_id])

                    # 发送至其他群
                    sql = """SELECT room_id, max(room_name) as room_name FROM {} group by room_id""".format('msg_records')
                    self.db.cursor.execute(sql)
                    for row in self.db.cursor.fetchall():
                        if '可达社区信息流' in row['room_name']:
                            forward_room = self.Room(room_id=row['room_id'])
                            await forward_room.ready()
                            try:
                                await forward_room.say(reply_link)
                            except Exception as e:
                                log.exception(e)

                    # 发送至Telegram
                    #threading.Thread(target=self.telegram.send_msg, args=(reply_url)).start()

                    return

                else:
                    reply = '未查到相关网页'
                    reply = reply + ' @{}'.format(talker.name)
                    await room.say(reply, mention_ids=[talker.contact_id])
                    return


        # 关键词回复
        if re.match(r'(资料|学习|学习资料|新人)', msg_text_inline):
            await self.send_msg_with_keyword('新手指南', contact=talker, room=room)
            return

        coin_dict = {
            'kda': 'kadena',
            'btc': 'bitcoin',
            'eth': 'ethereum',
            'dot': 'polkadot',
            'link': 'chainlink',
            'atom': 'cosmos',
            'mkr': 'maker',
            'luna': 'terra-luna',
            'celo': 'celo',
        }
        if room and msg_text.lower() in coin_dict:
            name = msg_text.lower()
            full_name = coin_dict[name]
            url = 'https://api.coingecko.com/api/v3/coins/{}/market_chart?vs_currency=usd&days=30&interval=daily'.format(full_name)
            data = requests.get(url).json()
            log.info('get chart, response: {}'.format(data))
            url = 'http://localhost:5000/chart-data'
            post_data = {
                'name': name.upper(),
                'prices': [],
                'volumes': [],
                'marketCaps': []
            }
            log.info(len(data['prices']))
            for i in range(len(data['prices'])):
                post_data['prices'].append({
                    'time': datetime.fromtimestamp(data['prices'][i][0] // 1000).strftime('%Y-%m-%d'),
                    'value': data['prices'][i][1],
                })
                post_data['volumes'].append('{:,d}'.format(int(data['total_volumes'][i][1])))
                post_data['marketCaps'].append('{:,d}'.format(int(data['market_caps'][i][1])))
            log.info('remove chart')
            os.system('cp chart/db-example.json chart/db.json')
            time.sleep(0.1)
            post_data = json.dumps(post_data)
            log.info('post data: {}'.format(post_data))
            headers = {'Content-Type': 'application/json'}
            time.sleep(0.5)
            res = requests.post(url, data=post_data, headers=headers)
            time.sleep(0.5)
            log.info('ready to fetch html')
            log.info('kkkkkk1')
            log.info('kkkkkk2')
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.driver.get('http://localhost:8000/')
            log.info('kkkkkk3')
            log.info('now get web')
            delay = 5
            try:
                log.info('kkkkkk4')
                myElem = WebDriverWait(self.driver, delay).until(EC.presence_of_element_located((By.ID, 'chart')))
                log.info('Page is ready!')
            except TimeoutException:
                log.indo('Loading took too much time!')

            # Create image to local
            file_path = '/var/www/html/{}-chart.png'.format(name)
            self.driver.save_screenshot(file_path)
            self.driver.quit()

            # Crop image
            log.info('now crop image')
            im = Image.open(file_path)
            im_cut = im.crop([0, 0, im.size[0], 350])
            im_cut.save(file_path)

            # Send image
            with open(file_path, 'rb') as f:
                content = base64.b64encode(f.read())
                file_box = FileBox.from_base64(name='{}-chart.png'.format(name), base64=content)
                await room.say(file_box)

            os.system('pkill -f chrome')

            return

        if msg_text == '可达秀':
            today = datetime.now()
            start_dt = datetime(today.year, today.month, today.day)
            sql = """SELECT contact_id, max(contact_name) as contact_name, sum(score) as score
                    FROM {} group by contact_id order by score desc""".format('kdashill_records')
            self.db.cursor.execute(sql)
            reply = '可达秀 [KDA-SHOW] \n活动积分当前排名与积分\n'
            records = list(self.db.cursor.fetchall())
            pool_score = sum([row['score'] for index, row in enumerate(records) if index >= 3])
            rank = 0
            for index, row in enumerate(records):
                rank += 1
                reply += '\n' + '{} - {}: {}分'.format(rank, row['contact_name'], row['score'])
                kda_cnt = 0
                if index == 0:
                    kda_cnt = 30
                elif index == 1:
                    kda_cnt = 20
                elif index == 2:
                    kda_cnt = 10
                else:
                    kda_cnt = round(40 * row['score'] / pool_score, 2)
                reply += ' - {}枚KDA'.format(kda_cnt)

            reply += '\n\n活动时间：3.18-3.24'

            await room.say(reply)

            return


        # AI回复
        if msg_type == 6 and (not room or '@{}'.format(self.my_contact_name) in msg_text):
            data = {
                'msg': msg_text,
                'appid': '0',
                'key': 'free'
            }
            url = 'http://api.qingyunke.com/api.php'
            res = requests.get(url, params=data)
            log.info('get AI request: {}, {}, response: {}'.format(url, data, res.text))
            data = res.json()
            reply = data['content'].replace('{br}', '\n')
            reply = reply + ' @{}'.format(talker.name)
            if room:
                await room.say(reply, mention_ids=[talker.contact_id])
            else:
                await msg.say(reply)


    async def on_room_join(self, room, invitees, inviter, date):
        await room.ready()
        invitee_names = ['@{} '.format(v.name) for v in invitees if v.name != self.my_contact_name]
        if invitee_names:
            reply = '欢迎新朋友加入可达社区！🍻\n阅读资料来快速了解Kadena吧~' + ' {}'.format(''.join(invitee_names))
            await room.say(reply)
            await self.send_msg_with_keyword('新手指南', room=room)

    def kick_member(self, talker, room, question):
        time.sleep(15)
        start_dt = datetime.now() - timedelta(minutes=1)
        sql = """SELECT msg_text FROM {} where contact_id = '{}' and created_at >= '{}'""".format('msg_records', talker.contact_id, start_dt)
        self.db.cursor.execute(sql)
        right_answer = self.ad_qa_dict[question]
        has_correct_answer = False
        for row in self.db.cursor.fetchall():
            log.info('fetch {}, answer = {}'.format(row['msg_text'], right_answer))
            if right_answer.lower() in row['msg_text'].lower():
                has_correct_answer = True

        loop = asyncio.new_event_loop()
        if has_correct_answer == False:
            reply = '本鸭最讨厌广告了！！！\n现在就把你抱出去/:<@' + ' @{}'.format(talker.name)
            log.info('ready to kick out {}'.format(reply))
            async def multiple_tasks():
                input_coroutines = [
                    room.say(reply, mention_ids=[talker.contact_id]),
                    room.delete(talker)
                ]
                await asyncio.gather(*input_coroutines, return_exceptions=True)

            asyncio.new_event_loop().run_until_complete(multiple_tasks())
        else:
            reply = '恭喜回答正确，误会解除~~~' + '@{}'.format(talker.name)
            asyncio.new_event_loop().run_until_complete(room.say(reply, mention_ids=[talker.contact_id]))

    async def send_msg_with_keyword(self, keyword, contact=None, room=None):
        sql = """SELECT msg_id FROM {} where keyword = '{}' order by created_at desc limit 1""".format('materials', keyword)
        self.db.cursor.execute(sql)
        msg_id = list(self.db.cursor.fetchall())[0]['msg_id']
        refer_msg = self.Message(message_id=msg_id)
        await refer_msg.ready()
        #await self.forward(msg, refer_msg)
        if room:
            await refer_msg.forward(room)
        else:
            await refer_msg.forward(talker)

    async def forward(self, msg, refer_msg):
        wrapped = None
        msg_type = refer_msg.message_type()
        if msg_type == 6:
            log.info('wrap to text')
            wrapped = refer_msg.text()
        elif msg_type == 3:
            log.info('wrap to contact')
            wrapped = await refer_msg.to_contact()
        elif msg_type in [1, 2, 4, 5, 7]:
            log.info('wrap to filebox')
            wrapped = await refer_msg.to_file_box()
        elif msg_type == 14:
            log.info('wrap to urllink')
            wrapped = await refer_msg.to_url_link()
        else:
            log.info('cannot wrapt to any type')
            return

        await msg.say(wrapped)


