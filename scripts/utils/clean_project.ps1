# WeMediaBaby Clean Script
# 项目清理工具 - 清理构建产物和打包缓存 (Nuitka & PyInstaller)
# File Encoding: UTF-8

$ErrorActionPreference = "Continue"

Write-Host "====================================="
Write-Host "     WeMediaBaby Clean Tool v1.2    "
Write-Host "====================================="
Write-Host ""
Write-Host "This tool will clean:" -ForegroundColor Yellow
Write-Host "  - Build/Dist folders (Nuitka & PyInstaller artifacts)"
Write-Host "  - Nuitka cache (*.build, *.dist, *.onefile-build)"
Write-Host "  - Python cache (__pycache__, *.pyc, *.pyo)"
Write-Host "  - Other caches (.pytest_cache, .mypy_cache, .tox)"
Write-Host "  - Log files (logs/*.log)"
Write-Host ""
Write-Host "Source code will NOT be affected." -ForegroundColor Green
Write-Host ""

$msg = "Confirm cleaning? (Y/N)"
$confirmation = Read-Host $msg

if ($confirmation -eq "Y" -or $confirmation -eq "y") {
    Write-Host ""
    Write-Host "Starting cleanup..." -ForegroundColor Cyan
    Write-Host "-------------------------------------"
    
    
    # 0. 终止占用进程
    Write-Host "[0/6] Checking for running processes..." -ForegroundColor White
    $processesToKill = @("WeMediaBaby", "QtWebEngineProcess", "main") 
    foreach ($procName in $processesToKill) {
        $procs = Get-Process -Name $procName -ErrorAction SilentlyContinue
        if ($procs) {
            Write-Host "  - Stopping process: $procName" -ForegroundColor Yellow
            Stop-Process -Name $procName -Force -ErrorAction SilentlyContinue
        }
    }
    # 等待进程完全释放文件锁
    Start-Sleep -Seconds 2

    # 1. 清理基础目录
    Write-Host "[1/6] Cleaning build directories (Nuitka & PyInstaller)..." -ForegroundColor White
    $basicTargets = @("build", "dist", "docs_backup")
    foreach ($t in $basicTargets) {
        if (Test-Path $t) {
            Write-Host "  - Removing: $t" -ForegroundColor Gray
            # 尝试先改名再删除，有时可以解决占用问题 (Optional trick, but Force Recurse usually works)
            Remove-Item -Path $t -Recurse -Force -ErrorAction Continue
            
            # Double check if it still exists (e.g. dist/fast)
            if (Test-Path $t) {
                 Write-Host "    - Warning: $t could not be fully removed. Retrying..." -ForegroundColor Yellow
                 Start-Sleep -Seconds 1
                 Remove-Item -Path $t -Recurse -Force -ErrorAction Continue
            }
        }
    }
    
    # 2. 清理 Nuitka 打包缓存
    Write-Host "[2/6] Cleaning Nuitka packaging cache..." -ForegroundColor White
    # Nuitka 生成的缓存目录模式: main.build, main.dist, main.onefile-build
    $nuitkaPatterns = @("*.build", "*.dist", "*.onefile-build")
    foreach ($pattern in $nuitkaPatterns) {
        Get-ChildItem -Path . -Directory -Filter $pattern -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  - Removing: $($_.Name)" -ForegroundColor Gray
            Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    # 清理 nuitka-crash-report.xml
    if (Test-Path "nuitka-crash-report.xml") {
        Write-Host "  - Removing: nuitka-crash-report.xml" -ForegroundColor Gray
        Remove-Item -Path "nuitka-crash-report.xml" -Force -ErrorAction SilentlyContinue
    }

    # 清理 PyInstaller 可能生成的临时 spec 文件（保留 main.spec）
    Get-ChildItem -Path . -Filter "*.spec" -File -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Name -ne "main.spec") {
            Write-Host "  - Removing temporary spec: $($_.Name)" -ForegroundColor Gray
            Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    
    # 3. 清理 Python 缓存
    Write-Host "[3/6] Cleaning Python cache..." -ForegroundColor White
    # 清理 __pycache__ 目录
    $pycacheCount = 0
    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        $pycacheCount++
    }
    Write-Host "  - Removed $pycacheCount __pycache__ directories" -ForegroundColor Gray
    
    # 清理 .pyc 和 .pyo 文件
    $pycFiles = Get-ChildItem -Path . -Recurse -Include "*.pyc", "*.pyo" -File -ErrorAction SilentlyContinue
    if ($pycFiles) {
        $pycFiles | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "  - Removed $($pycFiles.Count) .pyc/.pyo files" -ForegroundColor Gray
    }
    
    # 清理 egg-info 目录
    Get-ChildItem -Path . -Recurse -Directory -Filter "*.egg-info" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "  - Removing: $($_.Name)" -ForegroundColor Gray
        Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # 4. 清理测试和类型检查缓存
    Write-Host "[4/6] Cleaning test/lint cache..." -ForegroundColor White
    $testCacheTargets = @(".pytest_cache", ".mypy_cache", ".tox", ".hypothesis")
    foreach ($t in $testCacheTargets) {
        if (Test-Path $t) {
            Write-Host "  - Removing: $t" -ForegroundColor Gray
            Remove-Item -Path $t -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    
    # 5. 清理覆盖率报告
    Write-Host "[5/6] Cleaning coverage reports..." -ForegroundColor White
    $coverageTargets = @(".coverage", "htmlcov", "coverage.xml")
    foreach ($t in $coverageTargets) {
        if (Test-Path $t) {
            Write-Host "  - Removing: $t" -ForegroundColor Gray
            Remove-Item -Path $t -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    
    # 6. 清理日志文件
    Write-Host "[6/6] Cleaning log files..." -ForegroundColor White
    if (Test-Path "logs") {
        $logFiles = Get-ChildItem -Path "logs" -Filter "*.log" -ErrorAction SilentlyContinue
        if ($logFiles) {
            $logFiles | Remove-Item -Force -ErrorAction SilentlyContinue
            Write-Host "  - Removed $($logFiles.Count) log files" -ForegroundColor Gray
        }
    }

    Write-Host "-------------------------------------"
    Write-Host ""
    Write-Host "Cleanup Completed!" -ForegroundColor Green
}
else {
    Write-Host ""
    Write-Host "Operation cancelled." -ForegroundColor Yellow
}

Write-Host "====================================="
pause
