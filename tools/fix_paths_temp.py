import os
import re

src = os.path.abspath('src')
count = 0
fail = []

# 匹配任意形式的 "文件路径: xxx" 行（包括全角冒号）
line_pattern = re.compile(r'[ \t]*文件路径[:：][^\n]*\n?')

for root, dirs, files in os.walk(src):
    for fname in files:
        if not fname.endswith('.py'):
            continue
        fp = os.path.join(root, fname)
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                c = f.read()
        except UnicodeDecodeError:
            fail.append(fp)
            continue

        nc = line_pattern.sub('', c)
        if nc != c:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(nc)
            count += 1

print(f'已修复 {count} 个文件')
if fail:
    print(f'以下文件编码损坏，无法处理（建议 git checkout 恢复）:')
    for f in fail:
        print(f'  {f}')
