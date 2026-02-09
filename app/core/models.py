"""AI model management and loading."""
import os
import logging
from pathlib import Path
from typing import Optional
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

# 모델 다운로드 URL
MODEL_URLS = {
    "RealESRGAN_x4plus": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "RealESRGAN_x4plus_anime_6B": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
    "RealESRNet_x4plus": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth",
    "RealESRGAN_x2plus": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
}


class ModelManager:
    """AI 모델 다운로드 및 관리."""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """모델 경로 반환 (없으면 다운로드)."""
        model_file = self.models_dir / f"{model_name}.pth"
        
        if model_file.exists():
            return model_file
        
        # 모델 다운로드
        if model_name in MODEL_URLS:
            logger.info(f"Downloading model: {model_name}")
            if self.download_model(model_name):
                return model_file
        
        logger.error(f"Model not found: {model_name}")
        return None
    
    def download_model(self, model_name: str, progress_callback=None) -> bool:
        """모델 다운로드."""
        if model_name not in MODEL_URLS:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        url = MODEL_URLS[model_name]
        output_path = self.models_dir / f"{model_name}.pth"
        
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc=model_name) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))
                            
                            if progress_callback:
                                progress = pbar.n / total_size * 100
                                progress_callback(progress)
                else:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logger.info(f"Model downloaded: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            if output_path.exists():
                output_path.unlink()
            return False
    
    def list_available_models(self):
        """사용 가능한 모델 목록."""
        return list(MODEL_URLS.keys())
    
    def list_downloaded_models(self):
        """다운로드된 모델 목록."""
        return [f.stem for f in self.models_dir.glob("*.pth")]
    
    def delete_model(self, model_name: str) -> bool:
        """모델 파일 삭제."""
        model_file = self.models_dir / f"{model_name}.pth"
        try:
            if model_file.exists():
                model_file.unlink()
                logger.info(f"Model deleted: {model_name}")
                return True
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
        return False
