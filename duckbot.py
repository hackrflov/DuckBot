import asyncio
from wechaty import Wechaty, Message, UrlLink
import requests
import time
from wechaty_puppet import get_logger
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import re
import cv2
import random
import threading
import concurrent.futures

log = get_logger('mybot')


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

    def set_db(self, db):
        self.db = db

    def set_crawler(self, crawler):
        self.crawler = crawler

    async def on_message(self, msg: Message):

        # 加载消息发送者
        talker = msg.talker()
        await talker.ready()

        # 忽略自己发的消息
        if talker.contact_id == self.my_contact_id:
            return

        # 加载聊天室信息
        room = msg.room()
        if room:
            await room.ready()

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
            'room_name': room.topic if room else None,
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

            elif 'c/kdashill' in msg_text:
                today = datetime.now()
                start_dt = datetime(today.year, today.month, today.day)
                sql = """SELECT contact_id, max(contact_name) as contact_name, count(*) as score
                        FROM {} group by contact_id""".format('kdashill_records')
                self.db.cursor.execute(sql)
                reply = '可达秀 [KDA-Shill] 活动积分排名\n'
                rank = 0
                for row in self.db.cursor.fetchall():
                    rank += 1
                    reply += '\n' + '{} - {}: {}分'.format(rank, row['contact_name'], row['score'])

                await room.say(reply)

            return


        # 推荐活动
        if room and re.match(r'.*bihu\.com.*', msg_text_inline):
            match_results = re.search(r'(?<=bihu\.com/shortcontent/)\d{1,}', msg_text_inline.lower())
            if match_results:
                content_id = match_results[0]
                log.info('get content id = {}'.format(content_id))
                data = None
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self.crawler.fetch_bihu, content_id)
                    data = future.result()

                log.info('fetched bihu data = {}'.format(data))
                if data:
                    content_inline = data['content'].replace('\n', '')
                    post_date = datetime.fromtimestamp(data['createTS'] // 1000)
                    if not re.match(r'.*(kda|kadena|可达).*', content_inline.lower()):
                        reply = '未发现Kadena相关信息哦~'
                        reply = reply + ' @{}'.format(talker.name)
                        await room.say(reply, mention_ids=[talker.contact_id])
                        return
                    elif datetime.now() - post_date > timedelta(days=1):
                        reply = '文章太过久远，不能算入哦~'
                        reply = reply + ' @{}'.format(talker.name)
                        await room.say(reply, mention_ids=[talker.contact_id])
                        return

                    # 展示
                    reply_url = 'https://m.bihu.com/shortcontent/{}'.format(content_id)
                    reply_title = '可达社区 @ {}'.format(talker.name)
                    if 'imageUrlList' in data:
                        prefix = 'https://oss-cdn1.bihu-static.com/'
                        reply_thumbnail = prefix + data['imageUrlList'][0]
                    else:
                        reply_thumbnail = ''
                    reply_description = data['content'][:60]
                    log.info('to create url_link: {},{},{},{}'.format(reply_url, reply_title, reply_thumbnail, reply_description))
                    reply_link = UrlLink.create(reply_url, reply_title, reply_thumbnail, reply_description)
                    log.info('url created')
                    await room.say(reply_link)

                    # 查重
                    sql = """SELECT * FROM {} where content_id = '{}'""".format('kdashill_records', content_id)
                    self.db.cursor.execute(sql)
                    if len(list(self.db.cursor.fetchall())):
                        reply = '文章已有录入哦~'
                        reply = reply + ' @{}'.format(talker.name)
                        await room.say(reply, mention_ids=[talker.contact_id])
                        return

                    # 记分
                    insert_data = {
                        'content_id': content_id,
                        'contact_id': talker.contact_id,
                        'contact_name': talker.name,
                        'room_id': room.room_id,
                        'created_at': datetime.now()
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
                    sql = """SELECT contact_id, count(*) as score FROM {} group by contact_id order by score desc""".format('kdashill_records')
                    self.db.cursor.execute(sql)
                    rank = 0
                    for row in self.db.cursor.fetchall():
                        rank += 1
                        if row['contact_id'] == talker.contact_id:
                            reply = '感谢参加可达秀 [KDA-Shill] 活动！🍻\n'
                            reply += '您当前积分为{}，排名为{}'.format(row['score'], rank)
                            break

                    reply = reply + ' @{}'.format(talker.name)
                    await room.say(reply, mention_ids=[talker.contact_id])
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

        # AI回复
        if msg_type == 6 and (not room or '@{}'.format(self.my_contact_name) in msg_text):
            data = {
                'msg': msg_text,
                'appid': '0',
                'key': 'free'
            }
            url = 'http://api.qingyunke.com/api.php'
            res = requests.get(url, params=data)
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


