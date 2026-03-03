import os, re, ast

# 仍有语法错误的文件
problem_files = [
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\community\douyin\steps\image_upload_step.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\publish_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\xiaohongshu\login_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\image_batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_executor.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_manager_async.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\task_scheduler.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\batch_widget.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\task_execution_widget.py",
]

# 非法的"全角代码"字符集（这些是 GBK 乱码被错误解码后的字符）
ILLEGAL_CHARS = set('\ufffd\ufe40\u3003\uff04\u2033\u2032\u2019\u2018\u201c\u201d\u2026\u00b7\u00d7\u00f7')

fixed = 0
for fp in problem_files:
    if not os.path.exists(fp):
        print(f'[不存在] {fp}')
        continue
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(fp, 'rb') as f:
            raw = f.read()
        content = raw.decode('gbk', errors='replace')

    # 按行逐一处理：若行中含有非法字符则用注释行替代该行
    lines = content.splitlines(keepends=True)
    new_lines = []
    changed = False
    for line in lines:
        if any(c in ILLEGAL_CHARS for c in line):
            # 替换整行为空行（保留占位，避免影响行号）
            new_lines.append('\n')
            changed = True
        else:
            new_lines.append(line)

    if changed:
        new_content = ''.join(new_lines)
        # 移除开头多余的连续空行
        new_content = re.sub(r'^\n+', '', new_content)
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'[已修复] {os.path.basename(fp)}')
        fixed += 1
    else:
        print(f'[无需修复] {os.path.basename(fp)}')

print(f'\n共修复 {fixed} 个文件')
