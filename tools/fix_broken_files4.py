import os, re

src_dir = os.path.abspath('src')
fixed = 0

# 记录中文编码被错误解码后常见的非法全角字型字符
# 这些字符在正常中文代码中不应出现
ILLEGAL_RANGES = [
    (0x2000, 0x206F),  # 通用标点
    (0x2100, 0x214F),  # 字母类符号（包含 ℃）
    (0x2190, 0x21FF),  # 箭头
    (0x2200, 0x22FF),  # 数学运算符
    (0x2300, 0x23FF),  # 杂项技术
    (0x2460, 0x24FF),  # 带括号字母/数字（如 ②）
    (0x2500, 0x257F),  # 制表符
    (0x2600, 0x27BF),  # 杂项符号
    (0x2E00, 0x2E7F),  # 补充标点（包含 ﹀）
    (0x3000, 0x303F),  # CJK 符号和标点（包含 〃）
    (0xFE30, 0xFE4F),  # CJK 兼容形式（包含 ﹀）
    (0xFF00, 0xFF60),  # 全角 ASCII（包含 ＄）
    (0xFFFC, 0xFFFF),  # 替换字符（包含 U+FFFD）
]

def is_illegal(char):
    cp = ord(char)
    for lo, hi in ILLEGAL_RANGES:
        if lo <= cp <= hi:
            return True
    return False

def line_has_illegal(line):
    return any(is_illegal(c) for c in line)

for root, dirs, files in os.walk(src_dir):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fp = os.path.join(root, fname)
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            continue  # 跳过无法读取的文件

        lines = content.splitlines(keepends=True)
        new_lines = []
        changed = False
        for line in lines:
            if line_has_illegal(line):
                new_lines.append('\n')  # 用空行替换
                changed = True
            else:
                new_lines.append(line)

        if changed:
            new_content = ''.join(new_lines)
            # 清理开头多余空行
            new_content = re.sub(r'^\n+', '', new_content)
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'[已修复] {os.path.relpath(fp, src_dir)}')
            fixed += 1

print(f'\n共处理 {fixed} 个文件')
