"""Preset management for common upscaling configurations."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class UpscalePreset:
    """업스케일 프리셋."""
    name: str
    description: str
    scale_factor: int
    model_name: str
    denoise_strength: float
    tile_size: int
    jpg_quality: int
    video_codec: str
    video_crf: int


# 기본 프리셋
DEFAULT_PRESETS = {
    "default": UpscalePreset(
        name="default",
        description="기본 설정 - 일반적인 사진/영상",
        scale_factor=2,
        model_name="RealESRGAN_x4plus",
        denoise_strength=0.5,
        tile_size=512,
        jpg_quality=95,
        video_codec="h264",
        video_crf=18
    ),
    "high_quality": UpscalePreset(
        name="high_quality",
        description="최고 품질 - 처리 시간 김",
        scale_factor=4,
        model_name="RealESRGAN_x4plus",
        denoise_strength=0.3,
        tile_size=512,
        jpg_quality=98,
        video_codec="h265",
        video_crf=15
    ),
    "fast": UpscalePreset(
        name="fast",
        description="빠른 처리 - 품질 중간",
        scale_factor=2,
        model_name="RealESRGAN_x4plus",
        denoise_strength=0.6,
        tile_size=256,
        jpg_quality=90,
        video_codec="h264",
        video_crf=23
    ),
    "anime": UpscalePreset(
        name="anime",
        description="애니메이션/일러스트 특화",
        scale_factor=4,
        model_name="RealESRGAN_x4plus_anime_6B",
        denoise_strength=0.4,
        tile_size=512,
        jpg_quality=95,
        video_codec="h264",
        video_crf=18
    ),
    "4k_target": UpscalePreset(
        name="4k_target",
        description="4K 해상도 목표",
        scale_factor=4,
        model_name="RealESRGAN_x4plus",
        denoise_strength=0.4,
        tile_size=512,
        jpg_quality=96,
        video_codec="h265",
        video_crf=16
    )
}


class PresetManager:
    """프리셋 저장/로드 관리."""
    
    def __init__(self, presets_file: str = "presets.json"):
        self.presets_file = Path(presets_file)
        self.presets: Dict[str, UpscalePreset] = {}
        self.load()
    
    def load(self):
        """프리셋 파일 로드."""
        # 기본 프리셋 로드
        self.presets = DEFAULT_PRESETS.copy()
        
        # 사용자 정의 프리셋 로드
        try:
            if self.presets_file.exists():
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for name, preset_data in data.items():
                    self.presets[name] = UpscalePreset(**preset_data)
                
                logger.info(f"Presets loaded from {self.presets_file}")
        except Exception as e:
            logger.error(f"Error loading presets: {e}")
    
    def save(self):
        """프리셋 파일 저장 (기본 제외)."""
        try:
            self.presets_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 기본 프리셋은 저장하지 않음
            user_presets = {
                name: asdict(preset) 
                for name, preset in self.presets.items() 
                if name not in DEFAULT_PRESETS
            }
            
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(user_presets, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Presets saved to {self.presets_file}")
        except Exception as e:
            logger.error(f"Error saving presets: {e}")
    
    def get(self, name: str) -> Optional[UpscalePreset]:
        """프리셋 가져오기."""
        return self.presets.get(name)
    
    def list(self) -> List[str]:
        """프리셋 이름 목록."""
        return list(self.presets.keys())
    
    def add(self, preset: UpscalePreset):
        """프리셋 추가."""
        self.presets[preset.name] = preset
        self.save()
    
    def remove(self, name: str) -> bool:
        """프리셋 삭제 (기본 프리셋은 삭제 불가)."""
        if name in DEFAULT_PRESETS:
            logger.warning(f"Cannot delete default preset: {name}")
            return False
        
        if name in self.presets:
            del self.presets[name]
            self.save()
            return True
        
        return False
