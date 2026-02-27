
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.common.path_manager import PathManager

print(f"APPDATA env: {os.environ.get('APPDATA')}")
print(f"LOCALAPPDATA env: {os.environ.get('LOCALAPPDATA')}")
print(f"PathManager.get_app_data_dir(): {PathManager.get_app_data_dir()}")
print(f"PathManager.get_db_path(): {PathManager.get_db_path()}")

db_path = PathManager.get_db_path()
if db_path.exists():
    print("Database file EXISTS.")
else:
    print("Database file Does NOT exist.")
