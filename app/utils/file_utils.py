"""File handling utilities."""
import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)

# 지원 포맷
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv', '.webm', '.m4v'}


def is_image(file_path: str) -> bool:
    """이미지 파일 여부 확인."""
    return Path(file_path).suffix.lower() in IMAGE_EXTENSIONS


def is_video(file_path: str) -> bool:
    """동영상 파일 여부 확인."""
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


def get_image_info(file_path: str) -> Optional[dict]:
    """
    이미지 정보 추출.
    
    Returns:
        {width, height, format, size_mb} 또는 None
    """
    try:
        with Image.open(file_path) as img:
            width, height = img.size
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
            
            return {
                'width': width,
                'height': height,
                'format': img.format,
                'size_mb': round(file_size, 2)
            }
    except Exception as e:
        logger.error(f"Error reading image info: {e}")
        return None


def get_video_info(file_path: str) -> Optional[dict]:
    """
    동영상 정보 추출 (ffprobe 사용).
    
    Returns:
        {width, height, duration, fps, codec, size_mb} 또는 None
    """
    try:
        import ffmpeg
        
        probe = ffmpeg.probe(file_path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        
        if not video_stream:
            return None
        
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        
        # FPS 계산
        fps_str = video_stream.get('r_frame_rate', '30/1')
        fps_parts = fps_str.split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
        
        # 길이
        duration = float(probe['format'].get('duration', 0))
        
        # 파일 크기
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        
        return {
            'width': width,
            'height': height,
            'duration': round(duration, 2),
            'fps': round(fps, 2),
            'codec': video_stream.get('codec_name', 'unknown'),
            'size_mb': round(file_size, 2)
        }
    except Exception as e:
        logger.error(f"Error reading video info: {e}")
        return None


def generate_output_filename(
    input_path: str,
    output_dir: str,
    preset_name: str = "",
    scale: int = 2,
    width: Optional[int] = None,
    height: Optional[int] = None,
    extension: Optional[str] = None,
    avoid_overwrite: bool = True
) -> str:
    """
    출력 파일명 생성.
    
    패턴: {원본명}_{preset}_{scale}x_{width}x{height}.{ext}
    """
    input_path = Path(input_path)
    base_name = input_path.stem
    ext = extension or input_path.suffix
    
    # 파일명 구성
    parts = [base_name]
    if preset_name:
        parts.append(preset_name)
    parts.append(f"{scale}x")
    if width and height:
        parts.append(f"{width}x{height}")
    
    filename = "_".join(parts) + ext
    output_path = Path(output_dir) / filename
    
    # 덮어쓰기 방지
    if avoid_overwrite and output_path.exists():
        counter = 1
        while output_path.exists():
            filename = "_".join(parts) + f"_{counter}" + ext
            output_path = Path(output_dir) / filename
            counter += 1
    
    return str(output_path)


def ensure_dir(directory: str) -> Path:
    """디렉토리 생성 (없으면)."""
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_temp_files(temp_dir: str, pattern: str = "*"):
    """임시 파일 정리."""
    try:
        temp_path = Path(temp_dir)
        if temp_path.exists():
            for file in temp_path.glob(pattern):
                try:
                    if file.is_file():
                        file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete {file}: {e}")
            logger.info(f"Cleaned temp files: {temp_dir}")
    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}")
