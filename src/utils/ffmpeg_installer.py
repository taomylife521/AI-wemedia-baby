"""
FFmpeg 安装检查工具
文件路径：src/utils/ffmpeg_installer.py
功能：检查 ffmpeg 是否安装，如果未安装则提供安装方法
"""

import os
import sys
import subprocess
import platform
import logging
import shutil
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def _find_ffmpeg_executable() -> Optional[str]:
    """查找 ffmpeg 可执行文件路径
    
    仅检查项目目录下的便携式安装（tools/ffmpeg/）
    
    Returns:
        ffmpeg 可执行文件的路径，如果未找到返回 None
    """
    # 仅检查项目目录下的便携式安装
    project_root = Path(__file__).parent.parent.parent
    portable_paths = [
        project_root / 'tools' / 'ffmpeg' / 'ffmpeg.exe',
        project_root / 'tools' / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
        project_root / 'ffmpeg' / 'ffmpeg.exe',
        project_root / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
    ]
    for path in portable_paths:
        if path.exists():
            logger.info(f"找到便携式 ffmpeg: {path}")
            return str(path)
    
    logger.warning("未找到项目目录下的便携式 ffmpeg 安装")
    return None


def check_ffmpeg_installed() -> Tuple[bool, Optional[str]]:
    """检查 ffmpeg 是否已安装
    
    Returns:
        (是否已安装, 版本信息或错误信息)
    """
    # 首先查找 ffmpeg 可执行文件
    ffmpeg_path = _find_ffmpeg_executable()
    
    if not ffmpeg_path:
        return False, "ffmpeg 未找到，请先安装"
    
    try:
        result = subprocess.run(
            [ffmpeg_path, '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # 提取版本信息
            version_line = result.stdout.split('\n')[0] if result.stdout else "已安装"
            return True, version_line
        else:
            return False, "ffmpeg 命令执行失败"
    except FileNotFoundError:
        return False, "ffmpeg 未找到，请先安装"
    except subprocess.TimeoutExpired:
        return False, "ffmpeg 检查超时"
    except Exception as e:
        return False, f"检查失败: {str(e)}"


def check_ffmpeg_python_installed() -> bool:
    """检查 ffmpeg-python 包是否已安装
    
    Returns:
        如果已安装返回 True，否则返回 False
    """
    try:
        import ffmpeg
        return True
    except ImportError:
        return False


def install_ffmpeg_python() -> Tuple[bool, str]:
    """安装 ffmpeg-python Python 包
    
    Returns:
        (是否成功, 消息)
    """
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'ffmpeg-python>=0.2.0'],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        if result.returncode == 0:
            return True, "ffmpeg-python 安装成功"
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            return False, f"安装失败: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, "安装超时，请检查网络连接"
    except Exception as e:
        return False, f"安装过程出错: {str(e)}"


def install_ffmpeg_windows() -> Tuple[bool, str]:
    """在 Windows 系统上安装 ffmpeg
    
    Returns:
        (是否成功, 消息)
    """
    system = platform.system()
    if system != 'Windows':
        return False, f"当前系统为 {system}，此函数仅支持 Windows"
    
    # 方法1: 尝试使用 imageio-ffmpeg（Python 包，包含 ffmpeg 二进制）
    try:
        logger.info("尝试使用 imageio-ffmpeg 安装 ffmpeg...")
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'imageio-ffmpeg'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            # imageio-ffmpeg 安装后需要配置环境变量或使用其提供的路径
            try:
                import imageio_ffmpeg
                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
                logger.info(f"imageio-ffmpeg 安装成功，ffmpeg 路径: {ffmpeg_path}")
                # 将 ffmpeg 路径添加到当前进程的 PATH（临时）
                ffmpeg_dir = os.path.dirname(ffmpeg_path)
                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
                # 验证是否可用
                test_result = subprocess.run(
                    [ffmpeg_path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if test_result.returncode == 0:
                    return True, "使用 imageio-ffmpeg 安装成功，ffmpeg 已可用"
            except Exception as e:
                logger.warning(f"imageio-ffmpeg 配置失败: {e}")
    except Exception as e:
        logger.warning(f"imageio-ffmpeg 安装出错: {e}")
    
    # 方法2: 尝试使用 winget（Windows 10/11 自带）
    try:
        logger.info("尝试使用 winget 安装 ffmpeg...")
        # 使用 --source winget 避免 msstore 源的问题
        result = subprocess.run(
            ['winget', 'install', 'Gyan.FFmpeg', '--source', 'winget', '--accept-package-agreements', '--accept-source-agreements'],
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        if result.returncode == 0:
            return True, "使用 winget 安装成功，请重启命令行后使用"
        else:
            error_output = result.stderr if result.stderr else result.stdout
            logger.warning(f"winget 安装失败: {error_output}")
            # 如果是因为需要指定源，尝试不带自动确认参数
            if '--source' in error_output or '源' in error_output:
                logger.info("尝试使用 winget 安装（指定源）...")
                result2 = subprocess.run(
                    ['winget', 'install', 'Gyan.FFmpeg', '--source', 'winget'],
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                if result2.returncode == 0:
                    return True, "使用 winget 安装成功，请重启命令行后使用"
    except FileNotFoundError:
        logger.warning("winget 未找到，尝试其他方法...")
    except subprocess.TimeoutExpired:
        logger.warning("winget 安装超时")
    except Exception as e:
        logger.warning(f"winget 安装出错: {e}")
    
    # 方法3: 尝试使用 scoop
    try:
        logger.info("尝试使用 scoop 安装 ffmpeg...")
        result = subprocess.run(
            ['scoop', 'install', 'ffmpeg'],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            return True, "使用 scoop 安装成功，请重启命令行后使用"
        else:
            logger.warning(f"scoop 安装失败: {result.stderr}")
    except FileNotFoundError:
        logger.warning("scoop 未找到，尝试其他方法...")
    except subprocess.TimeoutExpired:
        logger.warning("scoop 安装超时")
    except Exception as e:
        logger.warning(f"scoop 安装出错: {e}")
    
    # 方法4: 尝试使用 chocolatey
    try:
        logger.info("尝试使用 chocolatey 安装 ffmpeg...")
        result = subprocess.run(
            ['choco', 'install', 'ffmpeg', '-y'],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            return True, "使用 chocolatey 安装成功，请重启命令行后使用"
        else:
            logger.warning(f"chocolatey 安装失败: {result.stderr}")
    except FileNotFoundError:
        logger.warning("chocolatey 未找到，尝试其他方法...")
    except subprocess.TimeoutExpired:
        logger.warning("chocolatey 安装超时")
    except Exception as e:
        logger.warning(f"chocolatey 安装出错: {e}")
    
    # 方法5: 尝试使用 conda（如果环境中有 conda）
    try:
        conda_exe = os.environ.get('CONDA_EXE', 'conda')
        logger.info("尝试使用 conda 安装 ffmpeg...")
        result = subprocess.run(
            [conda_exe, 'install', '-c', 'conda-forge', 'ffmpeg', '-y'],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            return True, "使用 conda 安装成功，请重启命令行后使用"
        else:
            logger.warning(f"conda 安装失败: {result.stderr}")
    except FileNotFoundError:
        logger.warning("conda 未找到，尝试其他方法...")
    except subprocess.TimeoutExpired:
        logger.warning("conda 安装超时")
    except Exception as e:
        logger.warning(f"conda 安装出错: {e}")
    
    # 如果自动安装都失败，返回手动安装说明
    return False, """自动安装失败，请使用便携式安装（推荐）：

便携式安装（无需管理员权限，推荐）:
  1. 下载 ffmpeg 压缩包: https://www.gyan.dev/ffmpeg/builds/
     或: https://github.com/BtbN/FFmpeg-Builds/releases
     选择 "ffmpeg-release-essentials.zip" 或类似版本
  2. 解压到项目目录下的 tools/ffmpeg/ 文件夹
     确保 ffmpeg.exe 位于 tools/ffmpeg/ 目录下
  3. 程序会自动检测并使用此路径
  4. 无需配置 PATH 环境变量，无需重启

目录结构示例：
  wemedia-baby/
  ├── tools/
  │   └── ffmpeg/
  │       ├── ffmpeg.exe
  │       ├── ffplay.exe
  │       └── ffprobe.exe

安装完成后，刷新文件列表即可使用。

注意：本程序仅使用项目目录下的便携式安装，不会使用系统 PATH 中的 ffmpeg。"""


def install_ffmpeg_auto() -> Tuple[bool, str]:
    """自动检测系统并安装 ffmpeg
    
    Returns:
        (是否成功, 消息)
    """
    system = platform.system()
    
    if system == 'Windows':
        return install_ffmpeg_windows()
    elif system == 'Linux':
        return False, """Linux 系统请使用包管理器安装：
  Ubuntu/Debian: sudo apt-get install ffmpeg
  CentOS/RHEL: sudo yum install ffmpeg
  Arch: sudo pacman -S ffmpeg"""
    elif system == 'Darwin':  # macOS
        return False, """macOS 系统请使用 Homebrew 安装：
  brew install ffmpeg"""
    else:
        return False, f"不支持的系统: {system}"


def check_and_install_ffmpeg(install_if_missing: bool = False) -> Tuple[bool, str]:
    """检查并可选地安装 ffmpeg
    
    Args:
        install_if_missing: 如果未安装是否自动安装
    
    Returns:
        (是否已安装, 消息)
    """
    # 检查 ffmpeg 是否已安装
    is_installed, version_info = check_ffmpeg_installed()
    if is_installed:
        ffmpeg_path = _find_ffmpeg_executable()
        source = "便携式安装"
        if ffmpeg_path:
            # 确认是否为便携式安装
            if 'tools' in ffmpeg_path or Path(ffmpeg_path).parent.parent.name == 'ffmpeg':
                source = "便携式安装"
            else:
                source = "便携式安装"  # 默认显示便携式安装
        return True, f"ffmpeg 已安装 ({source}): {version_info}"
    
    # 检查 ffmpeg-python 包
    if not check_ffmpeg_python_installed():
        logger.info("ffmpeg-python 包未安装，正在安装...")
        success, msg = install_ffmpeg_python()
        if not success:
            return False, f"ffmpeg-python 安装失败: {msg}"
        logger.info("ffmpeg-python 安装成功")
    
    # 如果 ffmpeg 未安装且需要自动安装
    if not is_installed and install_if_missing:
        logger.info("ffmpeg 未安装，尝试自动安装...")
        success, msg = install_ffmpeg_auto()
        return success, msg
    
    # 返回未安装信息
    if not is_installed:
        install_msg = install_ffmpeg_auto()[1] if install_if_missing else "请手动安装 ffmpeg"
        return False, f"ffmpeg 未安装。{install_msg}"
    
    return True, version_info


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("检查 ffmpeg 安装状态...")
    is_installed, msg = check_and_install_ffmpeg(install_if_missing=False)
    print(f"结果: {is_installed}")
    print(f"消息: {msg}")

