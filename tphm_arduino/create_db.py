import psycopg2

conn = psycopg2.connect(
    dbname='postgres',  # 기본 관리 DB
    user='postgres',
    password='',  # 우분투에서 만든 postgres 비번
    host='localhost',
    port='' #접근포트
)

conn.autocommit = True  # DB/사용자 생성에는 자동 커밋 필요
cursor = conn.cursor()