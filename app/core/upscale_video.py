"""Video upscaling with frame-by-frame processing."""
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Callable
from .upscale_image import ImageUpscaler
from .ffmpeg_handler import FFmpegHandler

logger = logging.getLogger(__name__)


class VideoUpscaler:
    """동영상 업스케일러 (프레임 단위 처리)."""
    
    def __init__(
        self,
        image_upscaler: ImageUpscaler,
        ffmpeg_handler: FFmpegHandler,
        temp_dir: str = "temp"
    ):
        self.image_upscaler = image_upscaler
        self.ffmpeg = ffmpeg_handler
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def upscale_video(
        self,
        input_path: str,
        output_path: str,
        scale: int = 2,
        codec: str = "h264",
        crf: int = 18,
        preserve_audio: bool = True,
        start_time: float = 0,
        duration: Optional[float] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        동영상 업스케일.
        
        Args:
            input_path: 입력 동영상 경로
            output_path: 출력 동영상 경로
            scale: 배율
            codec: 코덱 (h264, h265)
            crf: 품질
            preserve_audio: 오디오 보존 여부
            start_time: 시작 시간
            duration: 처리 길이
            progress_callback: 진행률 콜백 (단계, 진행률)
            
        Returns:
            성공 여부
        """
        if not self.ffmpeg.is_available():
            logger.error("FFmpeg not available")
            return False
        
        try:
            logger.info(f"Upscaling video: {input_path}")
            
            # 작업 디렉토리 생성
            work_dir = self.temp_dir / Path(input_path).stem
            frames_in_dir = work_dir / "frames_in"
            frames_out_dir = work_dir / "frames_out"
            audio_file = work_dir / "audio.aac"
            
            # 기존 파일 정리
            if work_dir.exists():
                shutil.rmtree(work_dir)
            
            frames_in_dir.mkdir(parents=True)
            frames_out_dir.mkdir(parents=True)
            
            # 1. 프레임 추출
            logger.info("Step 1: Extracting frames")
            if progress_callback:
                progress_callback("프레임 추출 중...", 0)
            
            def extract_progress(p):
                if progress_callback:
                    progress_callback("프레임 추출 중...", p * 0.2)
            
            if not self.ffmpeg.extract_frames(
                input_path,
                str(frames_in_dir),
                start_time,
                duration,
                extract_progress
            ):
                logger.error("Failed to extract frames")
                return False
            
            # 2. 프레임 업스케일
            logger.info("Step 2: Upscaling frames")
            frame_files = sorted(frames_in_dir.glob("frame_*.png"))
            total_frames = len(frame_files)
            
            if total_frames == 0:
                logger.error("No frames extracted")
                return False
            
            for idx, frame_file in enumerate(frame_files):
                output_frame = frames_out_dir / frame_file.name
                
                # 진행률 업데이트
                frame_progress = ((idx + 1) / total_frames) * 100
                overall_progress = 20 + (frame_progress * 0.6)
                
                if progress_callback:
                    progress_callback(
                        f"프레임 업스케일 중... ({idx + 1}/{total_frames})",
                        overall_progress
                    )
                
                # 프레임 업스케일
                if not self.image_upscaler.upscale(
                    str(frame_file),
                    str(output_frame),
                    scale
                ):
                    logger.error(f"Failed to upscale frame: {frame_file}")
                    return False
            
            # 3. 오디오 추출 (필요 시)
            audio_path = None
            if preserve_audio:
                logger.info("Step 3: Extracting audio")
                if progress_callback:
                    progress_callback("오디오 추출 중...", 80)
                
                if self.ffmpeg.extract_audio(input_path, str(audio_file)):
                    audio_path = str(audio_file)
                else:
                    logger.warning("Failed to extract audio, continuing without audio")
            
            # 4. 프레임 결합
            logger.info("Step 4: Combining frames")
            if progress_callback:
                progress_callback("동영상 생성 중...", 85)
            
            # 원본 FPS 가져오기
            video_info = self.ffmpeg.get_video_info(input_path)
            fps = video_info.get('fps', 30) if video_info else 30
            
            def combine_progress(p):
                if progress_callback:
                    progress_callback("동영상 생성 중...", 85 + (p * 0.15))
            
            if not self.ffmpeg.combine_frames(
                str(frames_out_dir),
                output_path,
                fps,
                codec,
                crf,
                audio_path,
                combine_progress
            ):
                logger.error("Failed to combine frames")
                return False
            
            # 5. 임시 파일 정리
            logger.info("Step 5: Cleaning up")
            if progress_callback:
                progress_callback("완료", 100)
            
            shutil.rmtree(work_dir)
            
            logger.info(f"Video upscaling completed: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error upscaling video: {e}")
            return False
    
    def upscale_video_sample(
        self,
        input_path: str,
        output_path: str,
        start_time: float = 0,
        duration: float = 3,
        scale: int = 2,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        동영상 샘플 구간 업스케일 (미리보기용).
        
        Args:
            input_path: 입력 경로
            output_path: 출력 경로
            start_time: 시작 시간
            duration: 샘플 길이 (초)
            scale: 배율
            progress_callback: 진행률 콜백
            
        Returns:
            성공 여부
        """
        return self.upscale_video(
            input_path,
            output_path,
            scale=scale,
            start_time=start_time,
            duration=duration,
            progress_callback=progress_callback
        )
    
    def cleanup(self):
        """임시 파일 정리."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(parents=True)
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
