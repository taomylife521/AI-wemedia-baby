@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo      项目版本管理工具
echo ==========================================
echo.
echo  [1] 补丁更新 (Patch)  - 修复少量 Bug (例如 1.0.0 -> 1.0.1)
echo  [2] 次版本更新 (Minor) - 增加新功能 (例如 1.0.0 -> 1.1.0)
echo  [3] 主版本更新 (Major) - 重大架构变更 (例如 1.0.0 -> 2.0.0)
echo.
set /p choice="请输入选项 (1/2/3): "

if "%choice%"=="1" goto patch
if "%choice%"=="2" goto minor
if "%choice%"=="3" goto major
echo 无效的输入，请重新运行。
goto end

:patch
echo.
echo 正在执行补丁更新...
python scripts/update_version.py patch
goto end

:minor
echo.
echo 正在执行次版本更新...
python scripts/update_version.py minor
goto end

:major
echo.
echo 正在执行主版本更新...
python scripts/update_version.py major
goto end

:end
echo.
pause
