"""GPU detection and configuration utilities."""
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def detect_gpu() -> Tuple[bool, str]:
    """
    GPU 사용 가능 여부 및 디바이스 정보 반환.
    
    Returns:
        (gpu_available, device_info): GPU 가용성과 디바이스 정보
    """
    try:
        import torch
        
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            device_count = torch.cuda.device_count()
            memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            
            info = f"{device_name} ({memory_gb:.1f}GB) - {device_count} device(s)"
            logger.info(f"GPU detected: {info}")
            return True, info
        else:
            logger.info("CUDA not available, using CPU")
            return False, "CPU only"
            
    except ImportError:
        logger.warning("PyTorch not installed")
        return False, "PyTorch not installed"
    except Exception as e:
        logger.error(f"Error detecting GPU: {e}")
        return False, f"Error: {str(e)}"


def get_device(use_gpu: bool = True) -> str:
    """
    사용할 디바이스 반환 (cuda/cpu).
    
    Args:
        use_gpu: GPU 사용 여부
        
    Returns:
        'cuda' 또는 'cpu'
    """
    if not use_gpu:
        return 'cpu'
    
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except ImportError:
        return 'cpu'


def get_optimal_tile_size(use_gpu: bool = True) -> int:
    """
    GPU/CPU에 따른 최적 타일 크기 반환.
    
    Args:
        use_gpu: GPU 사용 여부
        
    Returns:
        타일 크기 (픽셀)
    """
    if not use_gpu:
        return 256  # CPU는 작은 타일
    
    try:
        import torch
        if torch.cuda.is_available():
            # GPU 메모리에 따라 타일 크기 조정
            memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            
            if memory_gb >= 8:
                return 512
            elif memory_gb >= 6:
                return 400
            else:
                return 256
        else:
            return 256
    except Exception:
        return 256


def clear_gpu_cache():
    """GPU 메모리 캐시 정리."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("GPU cache cleared")
    except Exception as e:
        logger.error(f"Error clearing GPU cache: {e}")
