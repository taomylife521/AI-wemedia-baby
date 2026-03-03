import os
import re

broken = [
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\login_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\publish_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\scripts.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\selectors.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\xiaohongshu\login_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\xiaohongshu\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\image_batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_executor.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_manager_async.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\checkpoint_manager_async.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\retry_strategy.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\task_scheduler.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\batch_widget.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\create_task_dialog.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\task_detail_dialog.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\task_execution_widget.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\data_center\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\data_center\pages\data_center_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\data_center\pages\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\interaction\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\interaction\pages\comment_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\interaction\pages\private_message_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\interaction\pages\__init__.py",
]

# 用于移除包含中文"路径"相关字样的文件路径注释行
line_pattern = re.compile(r'.*[\u6587][\u4ef6][\u8def][\u5f84][:\uff1a][^\n]*\n?')

fixed = 0
for fp in broken:
    if not os.path.exists(fp):
        continue
    try:
        # 用 latin-1 强制读取（不会因非 UTF-8 字节而抛错）
        with open(fp, 'r', encoding='latin-1') as f:
            content = f.read()
        
        # 将 latin-1 字节流还原为真实中文字节再解码
        raw_bytes = content.encode('latin-1')
        try:
            decoded = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            decoded = raw_bytes.decode('gbk', errors='replace')
        
        # 移除路径行
        cleaned = line_pattern.sub('', decoded)
        # 清理开头多余的空行（只保留至多一个）
        cleaned = re.sub(r'^\n{2,}', '\n', cleaned)
        
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        print(f'[已修复] {os.path.basename(fp)}')
        fixed += 1
    except Exception as e:
        print(f'[失败] {fp}: {e}')

print(f'\n共修复 {fixed} 个损坏文件')
