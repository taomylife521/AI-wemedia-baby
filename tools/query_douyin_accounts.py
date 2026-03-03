"""临时脚本：查询数据库中抖音平台账号的平台昵称"""
import os
import sys
import sqlite3

# 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def main():
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    db_path = os.path.join(local_app_data, "WeMediaBaby", "data", "database.db")
    if not os.path.exists(db_path):
        print("数据库文件不存在:", db_path)
        return
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT id, platform, platform_username, login_status, created_at "
        "FROM platform_accounts WHERE platform = 'douyin' ORDER BY id"
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        print("当前数据库中没有抖音平台的账号记录。")
    else:
        print("抖音平台账号（平台昵称）：")
        print("-" * 50)
        for r in rows:
            nick = r["platform_username"] or "(未设置昵称)"
            print(f"  ID: {r['id']}  昵称: {nick}  状态: {r['login_status']}")
        print("-" * 50)
        print(f"共 {len(rows)} 个抖音账号")

if __name__ == "__main__":
    main()
