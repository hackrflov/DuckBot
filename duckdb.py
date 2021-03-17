import pymysql
import settings

class DuckDB:

    def connect(self):
        mysql_config = {
            'host': settings.MYSQL_HOST,
            'port': settings.MYSQL_PORT,
            'user': settings.MYSQL_USER,
            'password': settings.MYSQL_PASSWORD,
            'db': 'duckbot',
            'cursorclass': pymysql.cursors.DictCursor,
            'charset': 'utf8mb4',
        }
        self.db = pymysql.connect(**mysql_config)
        self.cursor = self.db.cursor()
