"""Worker thread for processing tasks."""
import logging
from PySide6.QtCore import QThread, Signal
from .task_queue import TaskQueue, TaskStatus, TaskType, UpscaleTask
from .upscale_image import ImageUpscaler
from .upscale_video import VideoUpscaler
from .models import ModelManager
from .ffmpeg_handler import FFmpegHandler

logger = logging.getLogger(__name__)


class Worker(QThread):
    """작업 처리 워커 스레드."""
    
    # Signals
    task_started = Signal(str)  # task_id
    task_progress = Signal(str, str, float)  # task_id, message, progress
    task_completed = Signal(str)  # task_id
    task_failed = Signal(str, str)  # task_id, error
    all_tasks_completed = Signal()
    
    def __init__(
        self,
        task_queue: TaskQueue,
        model_manager: ModelManager,
        device: str = "cuda",
        tile_size: int = 512
    ):
        super().__init__()
        self.task_queue = task_queue
        self.model_manager = model_manager
        self.device = device
        self.tile_size = tile_size
        
        self.ffmpeg = FFmpegHandler()
        self.image_upscaler = None
        self.video_upscaler = None
        self.current_model = None
        
        self._running = False
        self._stop_requested = False
    
    def run(self):
        """메인 실행 루프."""
        self._running = True
        self._stop_requested = False
        
        logger.info("Worker thread started")
        
        while self._running and not self._stop_requested:
            # 다음 작업 가져오기
            task = self.task_queue.get_next_pending_task()
            
            if not task:
                # 더 이상 대기 작업이 없음
                break
            
            # 취소 확인
            if task.status == TaskStatus.CANCELLED:
                continue
            
            # 작업 처리
            try:
                self._process_task(task)
            except Exception as e:
                logger.error(f"Unexpected error processing task {task.task_id}: {e}")
                self.task_queue.update_task(
                    task.task_id,
                    status=TaskStatus.FAILED,
                    error=str(e)
                )
                self.task_failed.emit(task.task_id, str(e))
        
        # 정리
        self._cleanup()
        
        logger.info("Worker thread finished")
        self.all_tasks_completed.emit()
    
    def _process_task(self, task: UpscaleTask):
        """현재 작업 id 저장 후 작업 처리"""
        self.current_task_id = task.task_id

        logger.info(f"Processing task: {task.task_id}")
        
        # 작업 시작
        self.task_queue.update_task(
            task.task_id,
            status=TaskStatus.PROCESSING,
            progress=0
        )
        self.task_started.emit(task.task_id)
        
        # 모델 로드 (필요 시)
        if not self._load_model(task.model_name):
            self.task_queue.update_task(
                task.task_id,
                status=TaskStatus.FAILED,
                error="Failed to load model"
            )
            self.task_failed.emit(task.task_id, "Failed to load model")
            return
        
        # 작업 유형별 처리
        try:
            if task.task_type == TaskType.IMAGE:
                success = self._process_image_task(task)
            elif task.task_type in [TaskType.VIDEO, TaskType.VIDEO_SAMPLE]:
                success = self._process_video_task(task)
            else:
                logger.error(f"Unknown task type: {task.task_type}")
                success = False
            
            if success:
                self.task_queue.update_task(
                    task.task_id,
                    status=TaskStatus.COMPLETED,
                    progress=100
                )
                self.task_completed.emit(task.task_id)
            else:
                self.task_queue.update_task(
                    task.task_id,
                    status=TaskStatus.FAILED,
                    error="Processing failed"
                )
                self.task_failed.emit(task.task_id, "Processing failed")
        
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            self.task_queue.update_task(
                task.task_id,
                status=TaskStatus.FAILED,
                error=str(e)
            )
            self.task_failed.emit(task.task_id, str(e))

        finally:
            self.current_task_id = None
    
    def _load_model(self, model_name: str) -> bool:
        """AI 모델 로드."""
        if self.current_model == model_name and self.image_upscaler:
            return True
        
        try:
            # 모델 경로 가져오기
            model_path = self.model_manager.get_model_path(model_name)
            if not model_path:
                logger.error(f"Model not found: {model_name}")
                return False
            
            # 이미지 업스케일러 생성
            self.image_upscaler = ImageUpscaler(
                model_path=str(model_path),
                model_name=model_name,
                device=self.device,
                tile_size=self.tile_size
            )
            
            # 비디오 업스케일러 생성
            self.video_upscaler = VideoUpscaler(
                image_upscaler=self.image_upscaler,
                ffmpeg_handler=self.ffmpeg
            )
            
            self.current_model = model_name
            logger.info(f"Model loaded: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def _process_image_task(self, task: UpscaleTask) -> bool:
        """이미지 작업 처리."""
        
        if not self.image_upscaler:
            logger.error("Image upscaler not initialized")
            return False
        
        def progress_callback(progress):
            # 취소 확인
            if self._stop_requested or task.status == TaskStatus.CANCELLED:
                raise InterruptedError("Task cancelled")
            
            self.task_queue.update_task(
                task.task_id,
                progress=progress,
                message="업스케일 중..."
            )
            self.task_progress.emit(task.task_id, "업스케일 중...", progress)
        
        return self.image_upscaler.upscale_with_quality(
            input_path=task.input_path,
            output_path=task.output_path,
            scale=task.scale,
            jpg_quality=task.jpg_quality,
            png_compression=task.png_compression,
            webp_quality=task.webp_quality,
            webp_lossless=task.webp_lossless,
            progress_callback=progress_callback
        )
    
    def _process_video_task(self, task: UpscaleTask) -> bool:
        """동영상 작업 처리."""
        
        if not self.video_upscaler:
            logger.error("Video upscaler not initialized")
            return False
        
        def progress_callback(message, progress):
            # 취소 확인
            if task.status == TaskStatus.CANCELLED:
                raise InterruptedError("Task cancelled")
            
            self.task_queue.update_task(
                task.task_id,
                progress=progress,
                message=message
            )
            self.task_progress.emit(task.task_id, message, progress)
        
        if task.task_type == TaskType.VIDEO_SAMPLE:
            return self.video_upscaler.upscale_video_sample(
                input_path=task.input_path,
                output_path=task.output_path,
                start_time=task.sample_start,
                duration=task.sample_duration or 3,
                scale=task.scale,
                progress_callback=progress_callback
            )
        else:
            return self.video_upscaler.upscale_video(
                input_path=task.input_path,
                output_path=task.output_path,
                scale=task.scale,
                codec=task.video_codec,
                crf=task.video_crf,
                preserve_audio=task.preserve_audio,
                progress_callback=progress_callback
            )
    
    def _cleanup(self):
        """리소스 정리."""
        if self.image_upscaler:
            self.image_upscaler.cleanup()
        
        if self.video_upscaler:
            self.video_upscaler.cleanup()
    
    def stop(self):
        """워커 중지."""
        self._stop_requested = True

        # 현재 작업도 취소 상태로 변경 (progress_callback 에서 즉시 감지)
        current_task_id = getattr(self, "current_task_id", None)
        if current_task_id:
            self.task_queue.update_task(
                current_task_id,
                status=TaskStatus.CANCELLED,
                message="사용자에 의해 중지됨"
            )
        logger.info("Worker stop requested")
