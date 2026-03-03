@echo off
chcp 65001 >nul
cd /d %~dp0
setlocal EnableDelayedExpansion

REM 读取当前版本号
set "CURRENT_VER=unknown"
for /f "usebackq tokens=*" %%A in (`python -c "exec(open('src/version.py',encoding='utf-8').read());print(__version__)"`) do (
    set "CURRENT_VER=%%A"
)

echo.
echo  ==================================================
echo.
echo              媒 小 宝 构 建 工 具 v2.1
echo.
echo    当前版本: !CURRENT_VER!
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
set /p "choice=  请选择 [1/2/3]: "

if "!choice!"=="1" goto ask_version_fast
if "!choice!"=="2" goto ask_version_nuitka
if "!choice!"=="3" goto clean_build
echo.
echo  无效输入，请重新运行。
goto end

:ask_version_fast
set "BUILD_CMD=powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build\build_fast.ps1"
goto ask_version

:ask_version_nuitka
set "BUILD_CMD=powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build\build_nuitka.ps1"
goto ask_version

:ask_version
echo.
echo  --------------------------------------------------
echo    当前版本: !CURRENT_VER!
echo  --------------------------------------------------
echo.
echo    输入新版本号 (格式 X.Y.Z) 直接更新
echo    直接按回车 跳过，使用当前版本构建
echo.
set /p "NEW_VER=  新版本号: "

if "!NEW_VER!"=="" (
    echo.
    echo  使用当前版本 !CURRENT_VER! 继续构建...
    goto do_build
)

echo.
echo  正在更新版本号: !CURRENT_VER! -^> !NEW_VER! ...
python scripts\release\update_version.py set !NEW_VER!
if errorlevel 1 (
    echo.
    echo  版本号更新失败，终止构建。
    goto end
)
echo.

:do_build
echo.
echo  正在启动构建...
echo.
!BUILD_CMD!
goto end

:clean_build
echo.
echo  正在清理构建产物...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build\build_nuitka.ps1 -CleanOnly
if exist "dist\fast" rmdir /s /q "dist\fast"
if exist "build" rmdir /s /q "build"
echo  清理完成。
goto end

:end
echo.
pause
