@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo      媒小宝打包构建工具
echo ==========================================
echo.
echo  [1] 快速构建 (PyInstaller)
echo      - 速度快，适合开发测试
echo      - 生成目录: dist/fast/WeMediaBaby
echo.
echo  [2] 性能构建 (Nuitka)
echo      - 启动快、源码加密、防反编译
echo      - 编译时间较长，适合正式发布
echo      - 生成目录: dist/secure/main.dist
echo.
echo  [3] 清理构建文件
echo      - 删除 dist, build 等临时目录
echo.
set /p choice="请输入选项 (1/2/3): "

if "%choice%"=="1" goto fast_build
if "%choice%"=="2" goto nuitka_build
if "%choice%"=="3" goto clean_build
echo 无效的输入，请重新运行。
goto end

:fast_build
echo.
echo 正在启动 PyInstaller 快速构建...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_fast.ps1
goto end

:nuitka_build
echo.
echo 正在启动 Nuitka 性能构建...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_nuitka.ps1
goto end

:clean_build
echo.
echo 正在清理构建产物...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_nuitka.ps1 -CleanOnly
REM Also clean fast build if not covered
if exist "dist\fast" rmdir /s /q "dist\fast"
if exist "build" rmdir /s /q "build"
echo 清理完成。
goto end

:end
echo.
pause
