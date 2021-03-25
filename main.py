from duckbot import DuckBot
from duckdb import DuckDB
from duckcrawler import DuckCrawler
from ducktg import Telegram

import asyncio
import time
import os, signal

def get_pids():
    pids = []
    cur_pid = os.getpid()
    for line in os.popen('ps ax | grep main.py'):
        if 'grep' in line:
            continue
        fields = line.split()
        pid = int(fields[0])
        if pid == cur_pid:
            continue
        pids.append(pid)
    return pids

def kill_process():
    pids = get_pids()
    for pid in get_pids():
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)

async def main():
    await bot.start()

duck_db = DuckDB()
duck_db.connect()
duck_crawler = DuckCrawler()
telegram = Telegram()

bot = DuckBot()
bot.set_driver()
bot.set_db(duck_db)
bot.set_crawler(duck_crawler)
bot.set_telegram(telegram)

kill_process()
asyncio.run(main())
