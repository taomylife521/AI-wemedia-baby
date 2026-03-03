import os
import re

# 还有语法错误的文件列表
problem_files = [
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\community\douyin\steps\image_upload_step.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\login_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\publish_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\wechat_video\selectors.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\xiaohongshu\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\plugins\pro\xiaohongshu\login_plugin.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\pages\image_batch_publish_page.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_executor.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\batch_task_manager_async.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\checkpoint_manager_async.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\retry_strategy.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\services\task_scheduler.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\__init__.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\batch_widget.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\create_task_dialog.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\task_detail_dialog.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\batch\ui\task_execution_widget.py",
    r"D:\003vibe_coding\wemedia-baby\wemedia-baby\src\pro_features\data_center\pages\data_center_page.py",
]

fixed = 0
for fp in problem_files:
    if not os.path.exists(fp):
        continue
    try:
        # 先尝试 utf-8
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 用 latin-1 读取，转回 gbk 解码
            with open(fp, 'rb') as f:
                raw = f.read()
            try:
                content = raw.decode('gbk', errors='replace')
            except Exception:
                content = raw.decode('latin-1', errors='replace')

        # 移除包含乱码替换符(U+FFFD) 或 Unicode 转义路径的整行
        # 策略：移除顶部 docstring 块，并重建干净的空 docstring
        # 1. 移除顶部多行 docstring（第一个 """...""" 块）
        # 检查是否是以 """ 开头的文件（注释块）
        cleaned = content

        # 移除顶部 """ 文档块 (如果其中含有 \ufffd 乱码或路径字样)
        # 匹配第一个三引号块
        first_docstring_match = re.match(r'^"""([\s\S]*?)"""\s*', cleaned)
        if first_docstring_match:
            inner = first_docstring_match.group(1)
            has_garbage = '\ufffd' in inner or re.search(r'[dD]:\\', inner)
            if has_garbage:
                # 移除整个顶部 docstring
                cleaned = cleaned[first_docstring_match.end():]

        # 统一清理任意包含 \ufffd 字符的整行（乱码行）
        lines = cleaned.splitlines(keepends=True)
        clean_lines = []
        for line in lines:
            if '\ufffd' in line:
                # 尝试保留行号/结构，用空行占位
                clean_lines.append('\n')
            else:
                clean_lines.append(line)
        cleaned = ''.join(clean_lines)

        # 清理开头多余空行
        cleaned = re.sub(r'^\n+', '', cleaned)

        with open(fp, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        print(f'[已修复] {os.path.basename(fp)}')
        fixed += 1
    except Exception as e:
        print(f'[失败] {fp}: {e}')

print(f'\n共修复 {fixed} 个文件')
