"""
视频元数据提取工具
文件路径：src/utils/video_metadata.py
功能：使用 ffmpeg-python 提取视频文件的时长、分辨率等元数据
"""

import os
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    logger.warning("ffmpeg-python 未安装，无法提取视频元数据")

# 尝试配置 ffmpeg 路径
_FFMPEG_PATH = None
_FFMPEG_DIR = None

def _initialize_ffmpeg_path(force_refresh=False):
    """初始化 ffmpeg 路径配置
    
    Args:
        force_refresh: 是否强制重新查找（即使已经找到过）
    """
    global _FFMPEG_PATH, _FFMPEG_DIR
    if _FFMPEG_PATH is None or force_refresh:
        try:
            from .ffmpeg_installer import _find_ffmpeg_executable
            _FFMPEG_PATH = _find_ffmpeg_executable()
            if _FFMPEG_PATH:
                _FFMPEG_DIR = os.path.dirname(_FFMPEG_PATH)
                # 将 ffmpeg 目录添加到 PATH 环境变量（确保 ffprobe 也能找到）
                if _FFMPEG_DIR not in os.environ.get('PATH', ''):
                    os.environ['PATH'] = _FFMPEG_DIR + os.pathsep + os.environ.get('PATH', '')
                logger.info(f"找到 ffmpeg: {_FFMPEG_PATH}")
                logger.info(f"ffmpeg 目录: {_FFMPEG_DIR}")
            else:
                logger.warning("未找到 ffmpeg 可执行文件")
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"初始化 ffmpeg 路径失败: {e}")

# 初始化路径
_initialize_ffmpeg_path()


def check_ffmpeg_available() -> bool:
    """检查 ffmpeg 是否可用
    
    Returns:
        如果 ffmpeg 可用返回 True，否则返回 False
    """
    if not FFMPEG_AVAILABLE:
        return False
    
    # 重新初始化路径（确保使用最新路径）
    _initialize_ffmpeg_path(force_refresh=True)
    
    try:
        import subprocess
        # 使用找到的 ffmpeg 路径，如果没有则使用系统 PATH
        ffmpeg_cmd = _FFMPEG_PATH if _FFMPEG_PATH else 'ffmpeg'
        
        # 确保 PATH 包含 ffmpeg 目录（ffmpeg-python 需要找到 ffprobe）
        env = os.environ.copy()
        if _FFMPEG_DIR and _FFMPEG_DIR not in env.get('PATH', ''):
            env['PATH'] = _FFMPEG_DIR + os.pathsep + env.get('PATH', '')
        
        # 尝试运行 ffmpeg 命令检查是否可用
        result = subprocess.run(
            [ffmpeg_cmd, '-version'],
            capture_output=True,
            text=True,
            timeout=5,
            env=env
        )
        if result.returncode == 0:
            logger.debug(f"ffmpeg 可用: {ffmpeg_cmd}")
            return True
        else:
            logger.warning(f"ffmpeg 命令执行失败")
            return False
    except FileNotFoundError:
        logger.warning(f"ffmpeg 未找到")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg 检查超时")
        return False
    except Exception as e:
        logger.warning(f"检查 ffmpeg 可用性时出错: {e}")
        return False


def get_video_metadata(file_path: str) -> Dict[str, Any]:
    """提取视频文件的元数据
    
    Args:
        file_path: 视频文件路径
    
    Returns:
        包含以下键的字典：
        - duration: 视频时长（秒，float）
        - width: 视频宽度（像素，int）
        - height: 视频高度（像素，int）
        - resolution: 分辨率字符串（如 "1920x1080"，str）
        
        如果提取失败，返回的字典中对应值为 None
    
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: ffmpeg 不可用或文件不是有效的视频文件
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 重新初始化 ffmpeg 路径（确保每次调用时都是最新的）
    _initialize_ffmpeg_path(force_refresh=True)
    
    if not FFMPEG_AVAILABLE:
        logger.warning(f"ffmpeg-python 未安装，无法提取视频元数据: {file_path}")
        logger.warning("请安装 ffmpeg-python: pip install ffmpeg-python")
        logger.warning("并确保系统已安装 ffmpeg")
        return {
            'duration': None,
            'width': None,
            'height': None,
            'resolution': None
        }
    
    # 检查 ffmpeg 是否真的可用
    if not check_ffmpeg_available():
        logger.error(f"ffmpeg 不可用，无法提取视频元数据: {file_path}")
        if _FFMPEG_PATH:
            logger.error(f"找到的 ffmpeg 路径: {_FFMPEG_PATH}，但无法执行")
        else:
            logger.error("未找到 ffmpeg，请确保已安装 ffmpeg")
        return {
            'duration': None,
            'width': None,
            'height': None,
            'resolution': None
        }
    
    try:
        # 确保 PATH 环境变量包含 ffmpeg 目录（ffmpeg-python 需要找到 ffprobe）
        if _FFMPEG_DIR and _FFMPEG_DIR not in os.environ.get('PATH', ''):
            os.environ['PATH'] = _FFMPEG_DIR + os.pathsep + os.environ.get('PATH', '')
        
        # 使用 ffmpeg 探测视频信息
        probe = ffmpeg.probe(file_path)
        
        # 获取视频流信息
        video_stream = None
        for stream in probe.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break
        
        if not video_stream:
            raise ValueError("文件中未找到视频流")
        
        # 提取时长（秒）
        duration = None
        format_info = probe.get('format', {})
        if 'duration' in format_info:
            try:
                duration = float(format_info['duration'])
            except (ValueError, TypeError):
                logger.warning(f"无法解析视频时长: {format_info.get('duration')}")
        
        # 提取分辨率
        width = None
        height = None
        resolution = None
        
        if 'width' in video_stream and 'height' in video_stream:
            try:
                width = int(video_stream['width'])
                height = int(video_stream['height'])
                resolution = f"{width}x{height}"
            except (ValueError, TypeError) as e:
                logger.warning(f"无法解析视频分辨率: {e}")
        
        return {
            'duration': duration,
            'width': width,
            'height': height,
            'resolution': resolution
        }
    
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"ffmpeg 提取元数据失败: {error_msg}")
        # 不抛出异常，返回空值，让调用者决定如何处理
        return {
            'duration': None,
            'width': None,
            'height': None,
            'resolution': None
        }
    except Exception as e:
        logger.error(f"提取视频元数据时发生错误: {e}", exc_info=True)
        # 不抛出异常，返回空值，让调用者决定如何处理
        return {
            'duration': None,
            'width': None,
            'height': None,
            'resolution': None
        }


def format_duration(seconds: Optional[float]) -> str:
    """格式化视频时长为可读字符串
    
    Args:
        seconds: 时长（秒）
    
    Returns:
        格式化后的时长字符串，如 "01:23:45" 或 "12:34"
    """
    if seconds is None:
        return "未知"
    
    try:
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    except (ValueError, TypeError):
        return "未知"


def extract_video_thumbnail(file_path: str) -> Optional[str]:
    """提取视频缩略图（首帧）
    
    Args:
        file_path: 视频文件路径
        
    Returns:
        缩略图文件路径（临时文件），如果提取失败返回 None
    """
    if not os.path.exists(file_path):
        return None
        
    _initialize_ffmpeg_path()
    
    if not FFMPEG_AVAILABLE or not check_ffmpeg_available():
        logger.warning("ffmpeg 不可用，无法提取缩略图")
        return None
        
    try:
        import tempfile
        
        # 创建临时文件保存缩略图
        fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        
        # 确保 PATH 包含 ffmpeg 目录
        if _FFMPEG_DIR and _FFMPEG_DIR not in os.environ.get('PATH', ''):
            os.environ['PATH'] = _FFMPEG_DIR + os.pathsep + os.environ.get('PATH', '')
            
        # 提取第0秒的帧（首帧画面）
        (
            ffmpeg
            .input(file_path, ss=0)
            .filter('scale', 1280, -1)  # 保持 1280px 超清底稿
            .output(temp_path, vframes=1, qscale=2)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path
        else:
            logger.warning("缩略图提取失败：文件为空或未生成")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return None
            
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        logger.error(f"ffmpeg 提取缩略图失败: {error_msg}")
        return None
    except Exception as e:
        logger.error(f"提取缩略图时发生错误: {e}", exc_info=True)
        return None
