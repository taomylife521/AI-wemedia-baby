"""
用 GBK 编码重写 build.bat 和 version.bat
cmd.exe 只能正确处理系统默认编码(GBK)的批处理文件
UTF-8 BOM 会被当作第一行命令的一部分导致全面崩溃
"""
import pathlib

# ============================================================
# build.bat
# ============================================================
build_bat = '''@echo off
cd /d %~dp0
setlocal

echo.
echo  ==================================================
echo.
echo              媒 小 宝 构 建 工 具 v2.0
echo.
echo  ==================================================
echo.
echo    [1] 快速构建 - PyInstaller
echo        速度快，约2分钟，适合开发测试
echo.
echo    [2] 性能构建 - Nuitka
echo        源码加密，防反编译，适合正式发布
echo.
echo    [3] 清理全部构建产物
echo.
echo  ==================================================
echo.
set /p choice="  请选择 [1/2/3]: "

if "%choice%"=="1" goto fast_build
if "%choice%"=="2" goto nuitka_build
if "%choice%"=="3" goto clean_build
echo.
echo  无效输入，请重新运行。
goto end

:fast_build
echo.
echo  正在启动 PyInstaller 快速构建...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\build\\build_fast.ps1
goto end

:nuitka_build
echo.
echo  正在启动 Nuitka 性能构建...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\build\\build_nuitka.ps1
goto end

:clean_build
echo.
echo  正在清理构建产物...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\build\\build_nuitka.ps1 -CleanOnly
if exist "dist\\fast" rmdir /s /q "dist\\fast"
if exist "build" rmdir /s /q "build"
echo  清理完成。
goto end

:end
echo.
pause
'''

# ============================================================
# version.bat
# ============================================================
version_bat = '''@echo off
cd /d %~dp0
setlocal

echo.
echo  ==================================================
echo.
echo            媒 小 宝 版 本 管 理 v2.0
echo.
echo  ==================================================
echo.
echo    [1] 补丁更新 - 修复Bug     - 1.0.0 到 1.0.1
echo    [2] 功能更新 - 增加新功能  - 1.0.0 到 1.1.0
echo    [3] 大版本   - 重大架构变更 - 1.0.0 到 2.0.0
echo.
echo  ==================================================
echo.
set /p choice="  请选择 [1/2/3]: "

if "%choice%"=="1" goto patch
if "%choice%"=="2" goto minor
if "%choice%"=="3" goto major
echo.
echo  无效输入，请重新运行。
goto end

:patch
echo.
echo  正在执行补丁更新...
python scripts\\release\\update_version.py patch
goto end

:minor
echo.
echo  正在执行功能更新...
python scripts\\release\\update_version.py minor
goto end

:major
echo.
echo  正在执行大版本更新...
python scripts\\release\\update_version.py major
goto end

:end
echo.
pause
'''

for name, content in [('build.bat', build_bat), ('version.bat', version_bat)]:
    p = pathlib.Path(r'd:\003vibe_coding\wemedia-baby\wemedia-baby') / name
    p.write_text(content, encoding='gbk')
    raw = p.read_bytes()
    has_bom = raw[:3] == b'\xef\xbb\xbf'
    print(f'[OK] {name}: {len(raw)} bytes, BOM={has_bom}, GBK encoded')
