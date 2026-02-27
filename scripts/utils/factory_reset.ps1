# WeMediaBaby Factory Reset Wrapper
# This script delegates the actual reset logic to the Python implementation
# to avoid PowerShell encoding issues.

$ErrorActionPreference = "Stop"

# Use python from the virtual environment if available, otherwise system python
if (Test-Path ".venv\Scripts\python.exe") {
    $pythonPath = ".venv\Scripts\python.exe"
} else {
    $pythonPath = "python"
}

$scriptPath = Join-Path $PSScriptRoot "factory_reset.py"

# Pass all arguments (like -Force) to the Python script
& $pythonPath $scriptPath $args
