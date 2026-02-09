"""Settings management with JSON persistence."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    """앱 설정 데이터 클래스."""
    
    # 출력 설정
    output_directory: str = ""
    avoid_overwrite: bool = True
    
    # 업스케일 설정
    scale_factor: int = 2
    model_name: str = "RealESRGAN_x4plus"
    denoise_strength: float = 0.5
    use_gpu: bool = True
    tile_size: int = 512
    
    # 이미지 설정
    jpg_quality: int = 95
    png_compression: int = 6
    webp_quality: int = 90
    webp_lossless: bool = False
    
    # 동영상 설정
    video_codec: str = "h264"  # h264, h265
    video_crf: int = 18
    preserve_audio: bool = True
    target_fps: Optional[float] = None
    
    # UI 설정
    theme: str = "light"  # light, dark
    last_preset: str = "default"
    window_geometry: Dict[str, int] = None
    
    def __post_init__(self):
        if self.window_geometry is None:
            self.window_geometry = {'width': 1280, 'height': 720}


class SettingsManager:
    """설정 저장/로드 관리."""
    
    def __init__(self, settings_file: str = "settings.json"):
        self.settings_file = Path(settings_file)
        self.settings = AppSettings()
        self.load()
    
    def load(self) -> bool:
        """설정 파일 로드."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 딕셔너리를 AppSettings로 변환
                for key, value in data.items():
                    if hasattr(self.settings, key):
                        setattr(self.settings, key, value)
                
                logger.info(f"Settings loaded from {self.settings_file}")
                return True
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        
        return False
    
    def save(self) -> bool:
        """설정 파일 저장."""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.settings), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Settings saved to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정 값 가져오기."""
        return getattr(self.settings, key, default)
    
    def set(self, key: str, value: Any):
        """설정 값 설정."""
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            self.save()
        else:
            logger.warning(f"Unknown setting key: {key}")
    
    def reset(self):
        """설정 초기화."""
        self.settings = AppSettings()
        self.save()
