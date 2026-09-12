from app import app, db
from models import *

with app.app_context():
    # 导出所有建表语句
    sql = ""
    for table in db.metadata.sorted_tables:
        sql += str(table.compile(dialect=db.engine.dialect)) + ";\n\n"
    with open("建表语句.sql", "w", encoding="utf-8") as f:
        f.write(sql)
    print("SQL已导出到：建表语句.sql")