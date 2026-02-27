@echo off
chcp 65001 >nul
cd /d %~dp0
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
powershell -NoProfile -ExecutionPolicy Bypass -File build/build_fast.ps1
goto end

:nuitka_build
echo.
echo 正在启动 Nuitka 性能构建...
powershell -NoProfile -ExecutionPolicy Bypass -File build/build_nuitka.ps1
goto end

:clean_build
echo.
echo 正在清理构建产物...
powershell -NoProfile -ExecutionPolicy Bypass -File build/build_nuitka.ps1 -CleanOnly
REM Also clean fast build if not covered (relative to project root, need to resolve paths or use absolute)
REM Process is simpler: build_nuitka.ps1 handles cleanup of its own output.
REM build_fast.ps1 cleans 'dist/fast'.
REM Since we are in scripts/, we need to know where project root is to clean specific folders manually if scripts don't do it.
REM But build_nuitka.ps1 DOES navigate to project root. So relying on it is safe.
echo 清理完成。
goto end

:end
echo.
pause
