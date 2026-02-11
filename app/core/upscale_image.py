"""Image upscaling with Real-ESRGAN."""
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Callable
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

def _clean_path(p: str) -> str:
    # UI/로그/드래그앤드롭에서 개행이 섞여 들어오는 케이스 방어
    return str(p).strip().replace("\n", "").replace("\r", "")

def imread_unicode(path: str, flags=cv2.IMREAD_UNCHANGED):
    path = _clean_path(path)
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, flags)
    return img

def imwrite_unicode(path: str, img, params=None) -> bool:
    path = _clean_path(path)
    ext = Path(path).suffix.lower()
    if not ext:
        raise ValueError(f"Output path has no extension: {path}")

    # OpenCV 확장자는 '.png' 같이 점 포함 -> imencode는 'png' 형태 선호
    ext_no_dot = ext[1:]

    if params is None:
        params = []

    ok, encoded = cv2.imencode(f".{ext_no_dot}", img, params)
    if not ok:
        return False
    encoded.tofile(path)
    return True

class ImageUpscaler:
    """Real-ESRGAN 기반 이미지 업스케일러."""
    
    def __init__(
        self,
        model_path: str,
        model_name: str = "RealESRGAN_x4plus",
        device: str = "cuda",
        tile_size: int = 512,
        denoise_strength: float = 0.5
    ):
        self.model_path = model_path
        self.model_name = model_name
        self.device = device
        self.tile_size = tile_size
        self.denoise_strength = denoise_strength
        self.upsampler = None
        
        self._init_model()
    
    def _init_model(self):
        """Real-ESRGAN 모델 초기화."""
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
            
            # 모델 아키텍처 설정
            if 'anime' in self.model_name:
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
                netscale = 4
            else:
                model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
                netscale = 4
            
            # Upsampler 생성
            self.upsampler = RealESRGANer(
                scale=netscale,
                model_path=self.model_path,
                model=model,
                tile=self.tile_size,
                tile_pad=10,
                pre_pad=0,
                half=True if self.device == 'cuda' else False,
                device=self.device
            )
            
            logger.info(f"Model initialized: {self.model_name} on {self.device}")
            
        except Exception as e:
            logger.error(f"Error initializing model: {e}")
            raise
    
    def upscale(
        self,
        input_path: str,
        output_path: str,
        scale: int = 2,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        이미지 업스케일.
        
        Args:
            input_path: 입력 이미지 경로
            output_path: 출력 이미지 경로
            scale: 배율 (2, 3, 4)
            progress_callback: 진행률 콜백 함수
            
        Returns:
            성공 여부
        """
        try:
            logger.info(f"Upscaling: {input_path} -> {output_path}")
            
            # 이미지 로드
            input_path = _clean_path(input_path)
            output_path = _clean_path(output_path)

            img = imread_unicode(input_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"Failed to load image: {input_path}")
            
            if progress_callback:
                progress_callback(10)
            
            # 업스케일 수행
            if self.upsampler is None:
                raise RuntimeError("Upsampler not initialized")
            
            try:
                output, _ = self.upsampler.enhance(img, outscale=scale)
            except Exception as e:
                logger.error(f"Enhancement failed: {e}")
                raise
            
            if progress_callback:
                progress_callback(80)
            
            # 결과 저장
            ext = Path(output_path).suffix.lower()
            
            if ext in ['.jpg', '.jpeg']:
                ok = imwrite_unicode(output_path, output, [cv2.IMWRITE_JPEG_QUALITY, 95])
            elif ext == '.png':
                ok = imwrite_unicode(output_path, output, [cv2.IMWRITE_PNG_COMPRESSION, 6])
            elif ext == '.webp':
                ok = imwrite_unicode(output_path, output, [cv2.IMWRITE_WEBP_QUALITY, 90])
            else:
                ok = imwrite_unicode(output_path, output)

            if not ok:
                raise ValueError(f"Failed to save image: {output_path}")
            
            if progress_callback:
                progress_callback(100)
            
            logger.info(f"Upscaling completed: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error upscaling image: {e}")
            return False
    
    def upscale_with_quality(
        self,
        input_path: str,
        output_path: str,
        scale: int = 2,
        jpg_quality: int = 95,
        png_compression: int = 6,
        webp_quality: int = 90,
        webp_lossless: bool = False,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        품질 옵션을 지정한 업스케일.
        
        Args:
            input_path: 입력 경로
            output_path: 출력 경로
            scale: 배율
            jpg_quality: JPEG 품질 (0-100)
            png_compression: PNG 압축 레벨 (0-9)
            webp_quality: WEBP 품질 (0-100)
            webp_lossless: WEBP 무손실 여부
            progress_callback: 진행률 콜백
            
        Returns:
            성공 여부
        """
        try:
            logger.info(f"Upscaling with quality: {input_path}")
            
            # 이미지 로드
            input_path = _clean_path(input_path)
            output_path = _clean_path(output_path)

            img = imread_unicode(input_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"Failed to load image: {input_path}")
            
            if progress_callback:
                progress_callback(10)
            
            if self.upsampler is None:
                raise RuntimeError("Upsampler not initialized")
            
            # 업스케일
            output, _ = self.upsampler.enhance(img, outscale=scale)
            
            if progress_callback:
                progress_callback(80)
            
            # 포맷별 저장
            ext = Path(output_path).suffix.lower()
            
            if ext in ['.jpg', '.jpeg']:
                ok = imwrite_unicode(output_path, output, [cv2.IMWRITE_JPEG_QUALITY, jpg_quality])
            elif ext == '.png':
                ok = imwrite_unicode(output_path, output, [cv2.IMWRITE_PNG_COMPRESSION, png_compression])
            elif ext == '.webp':
                if webp_lossless:
                    ok = imwrite_unicode(output_path, output, [cv2.IMWRITE_WEBP_QUALITY, 101])
                else:
                    ok = imwrite_unicode(output_path, output, [cv2.IMWRITE_WEBP_QUALITY, webp_quality])
            else:
                ok = imwrite_unicode(output_path, output)

            if not ok:
                raise ValueError(f"Failed to save image: {output_path}")

            if progress_callback:
                progress_callback(100)
            
            logger.info(f"Saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
    
    def cleanup(self):
        """리소스 정리."""
        self.upsampler = None
        
        # GPU 캐시 정리
        if self.device == 'cuda':
            try:
                import torch
                torch.cuda.empty_cache()
            except:
                pass
