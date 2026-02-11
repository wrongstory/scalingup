"""FFmpeg wrapper for video processing."""
import os
import re
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Callable, Dict

logger = logging.getLogger(__name__)

def _clean_path(p: str) -> str:
    return str(p).strip().replace("\n", "").replace("\r", "")


class FFmpegHandler:
    """FFmpeg 래퍼 클래스."""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
        
        if not self.ffmpeg_path:
            logger.warning("FFmpeg not found in PATH")
    
    def _find_ffmpeg(self) -> Optional[str]:
        """FFmpeg 실행 파일 찾기."""
        # PATH에서 찾기
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        
        # Windows 기본 경로 확인
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _find_ffprobe(self) -> Optional[str]:
        """FFprobe 실행 파일 찾기."""
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            return ffprobe
        
        common_paths = [
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            os.path.join(os.getcwd(), "ffmpeg", "bin", "ffprobe.exe"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def is_available(self) -> bool:
        """FFmpeg 사용 가능 여부."""
        return self.ffmpeg_path is not None
    
    def get_video_info(self, video_path: str) -> Optional[Dict]:
        """동영상 정보 추출."""
        if not self.ffprobe_path:
            logger.error("FFprobe not found")
            return None
        
        try:
            video_path = _clean_path(video_path)
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                
                # 비디오 스트림 찾기
                video_stream = next(
                    (s for s in info.get('streams', []) if s.get('codec_type') == 'video'),
                    None
                )
                
                if video_stream:
                    # FPS 계산
                    fps_str = video_stream.get('r_frame_rate', '30/1')
                    fps_parts = fps_str.split('/')
                    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
                    
                    return {
                        'width': int(video_stream.get('width', 0)),
                        'height': int(video_stream.get('height', 0)),
                        'duration': float(info.get('format', {}).get('duration', 0)),
                        'fps': fps,
                        'codec': video_stream.get('codec_name', 'unknown'),
                        'bitrate': int(info.get('format', {}).get('bit_rate', 0))
                    }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
        
        return None
    
    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        start_time: float = 0,
        duration: Optional[float] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        동영상에서 프레임 추출.
        
        Args:
            video_path: 동영상 경로
            output_dir: 출력 디렉토리
            start_time: 시작 시간 (초)
            duration: 추출 길이 (초, None이면 끝까지)
            progress_callback: 진행률 콜백
            
        Returns:
            성공 여부
        """
        if not self.ffmpeg_path:
            logger.error("FFmpeg not found")
            return False
        
        try:
            video_path = _clean_path(video_path)
            output_dir = _clean_path(output_dir)
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            out_pattern = str(Path(output_dir) / "frame_%06d.png")
            
            cmd = [
                self.ffmpeg_path, "-y",
                "-ss", str(start_time),
            ]
            
            if duration:
                cmd.extend(["-t", str(duration)])
            
            cmd.extend([
                "-i", video_path,
                "-qscale:v", "1",
                out_pattern
            ])

            # 콜백 없으면 데드락 방지
            if not progress_callback:
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return result.returncode == 0
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                universal_newlines=True
            )

            # 진행률 파싱
            video_info = self.get_video_info(video_path)
            total_duration = duration or video_info.get('duration', 0) if video_info else 0
                
            assert process.stderr is not None
            for line in process.stderr:
                time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if time_match and total_duration > 0:
                    h, m, s = map(float, time_match.groups())
                    current_time = h * 3600 + m * 60 + s
                    progress = min(100, (current_time / total_duration) * 100)
                    progress_callback(progress)
            
            process.wait()
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            return False
    
    def combine_frames(
        self,
        frames_dir: str,
        output_path: str,
        fps: float = 30,
        codec: str = "h264",
        crf: int = 18,
        audio_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> bool:
        """
        프레임을 동영상으로 결합.
        
        Args:
            frames_dir: 프레임 디렉토리
            output_path: 출력 동영상 경로
            fps: 프레임레이트
            codec: 코덱 (h264, h265)
            crf: 품질 (0-51, 낮을수록 고품질)
            audio_path: 오디오 파일 경로 (원본 동영상)
            progress_callback: 진행률 콜백
            
        Returns:
            성공 여부
        """
        if not self.ffmpeg_path:
            logger.error("FFmpeg not found")
            return False
        
        try:
            frames_dir = _clean_path(frames_dir)
            output_path = _clean_path(output_path)
            audio_path = _clean_path(audio_path) if audio_path else None

            # 코덱 설정
            codec_name = "libx264" if codec == "h264" else "libx265"
            in_pattern = str(Path(frames_dir) / "frame_%06d.png")
            
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-framerate", str(fps),
                "-i", in_pattern,
                "-c:v", codec_name,
                "-crf", str(crf),
                "-pix_fmt", "yuv420p",
            ]
            
            # 오디오 추가
            if audio_path:
                cmd.extend([
                    "-i", audio_path,
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest"
                ])

            cmd.append(output_path)
            
            if not progress_callback:
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return result.returncode == 0
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            
            # 진행률 파싱
            frame_files = list(Path(frames_dir).glob("frame_*.png"))
            total_frames = len(frame_files)
            
            assert process.stderr is not None
            for line in process.stderr:
                frame_match = re.search(r'frame=\s*(\d+)', line)
                if frame_match and total_frames > 0:
                    current_frame = int(frame_match.group(1))
                    progress = min(100, (current_frame / total_frames) * 100)
                    progress_callback(progress)
            
            process.wait()
            
            return process.returncode == 0
            
        except Exception as e:
            logger.error(f"Error combining frames: {e}")
            return False
    
    def extract_audio(self, video_path: str, output_path: str) -> bool:
        """동영상에서 오디오 추출."""
        if not self.ffmpeg_path:
            return False
        
        try:
            video_path = _clean_path(video_path)
            output_path = _clean_path(output_path)

            cmd = [self.ffmpeg_path, "-y", "-i", video_path, "-vn", "-acodec", "copy", output_path]
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            return False
