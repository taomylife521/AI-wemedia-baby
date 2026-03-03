"""
批量修复编码损坏的 Python 文件：
用 GBK 解码字节流后，重新以 UTF-8 写回，并移除头部文件路径行
"""
import os, re

# 有问题的文件列表（不在 git 历史，无法 checkout 恢复）
PROBLEM_FILES = [
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\publish_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\xiaohongshu\login_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\image_batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_executor.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_manager_async.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\batch_widget.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\task_detail_dialog.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\task_execution_widget.py",
]

LINE_PATH_PATTERN = re.compile(r'^\s*文件路径[:：][^\n]*\n?', re.MULTILINE)

fixed = 0
for fp in PROBLEM_FILES:
    if not os.path.exists(fp):
        print(f'[不存在] {fp}')
        continue
    try:
        # 以二进制读取，用 GBK 解码（大多数原始中文 Windows 文件使用 GBK）
        with open(fp, 'rb') as f:
            raw = f.read()
        
        decoded = raw.decode('gbk', errors='ignore')
        
        # 移除路径行
        cleaned = LINE_PATH_PATTERN.sub('', decoded)
        
        # 以 UTF-8 写回
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        
        print(f'[已修复] {os.path.basename(fp)}')
        fixed += 1
    except Exception as e:
        print(f'[失败] {fp}: {e}')

print(f'\n共修复 {fixed} 个文件')
