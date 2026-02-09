"""Task queue management for batch processing."""
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """작업 상태."""
    PENDING = "대기"
    PROCESSING = "처리중"
    COMPLETED = "완료"
    FAILED = "실패"
    CANCELLED = "취소됨"


class TaskType(Enum):
    """작업 유형."""
    IMAGE = "이미지"
    VIDEO = "동영상"
    VIDEO_SAMPLE = "동영상 샘플"


@dataclass
class UpscaleTask:
    """업스케일 작업."""
    
    # 기본 정보
    task_id: str
    task_type: TaskType
    input_path: str
    output_path: str
    
    # 업스케일 설정
    scale: int = 2
    model_name: str = "RealESRGAN_x4plus"
    
    # 이미지 설정
    jpg_quality: int = 95
    png_compression: int = 6
    webp_quality: int = 90
    webp_lossless: bool = False
    
    # 동영상 설정
    video_codec: str = "h264"
    video_crf: int = 18
    preserve_audio: bool = True
    sample_start: float = 0
    sample_duration: Optional[float] = None
    
    # 상태 정보
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    
    # 타임스탬프
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if isinstance(self.task_type, str):
            self.task_type = TaskType[self.task_type]
        if isinstance(self.status, str):
            self.status = TaskStatus[self.status]


class TaskQueue:
    """작업 큐 관리."""
    
    def __init__(self):
        self.tasks: List[UpscaleTask] = []
        self.current_task: Optional[UpscaleTask] = None
        self._task_counter = 0
    
    def add_task(self, task: UpscaleTask) -> str:
        """작업 추가."""
        if not task.task_id:
            self._task_counter += 1
            task.task_id = f"task_{self._task_counter:04d}"
        
        self.tasks.append(task)
        logger.info(f"Task added: {task.task_id}")
        return task.task_id
    
    def get_task(self, task_id: str) -> Optional[UpscaleTask]:
        """작업 조회."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def get_next_pending_task(self) -> Optional[UpscaleTask]:
        """다음 대기 작업 가져오기."""
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                return task
        return None
    
    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        error: Optional[str] = None
    ):
        """작업 상태 업데이트."""
        task = self.get_task(task_id)
        if not task:
            return
        
        if status is not None:
            task.status = status
            
            if status == TaskStatus.PROCESSING and not task.started_at:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()
        
        if progress is not None:
            task.progress = progress
        
        if message is not None:
            task.message = message
        
        if error is not None:
            task.error = error
    
    def remove_task(self, task_id: str) -> bool:
        """작업 제거."""
        task = self.get_task(task_id)
        if task:
            # 처리 중인 작업은 제거 불가
            if task.status == TaskStatus.PROCESSING:
                logger.warning(f"Cannot remove processing task: {task_id}")
                return False
            
            self.tasks.remove(task)
            logger.info(f"Task removed: {task_id}")
            return True
        
        return False
    
    def cancel_task(self, task_id: str) -> bool:
        """작업 취소."""
        task = self.get_task(task_id)
        if task:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                logger.info(f"Task cancelled: {task_id}")
                return True
            elif task.status == TaskStatus.PROCESSING:
                # 처리 중인 작업은 플래그만 설정
                # 실제 취소는 Worker가 처리
                task.status = TaskStatus.CANCELLED
                logger.info(f"Cancellation requested: {task_id}")
                return True
        
        return False
    
    def clear_completed(self):
        """완료/실패/취소된 작업 제거."""
        self.tasks = [
            task for task in self.tasks
            if task.status == TaskStatus.PENDING or task.status == TaskStatus.PROCESSING
        ]
    
    def clear_all(self):
        """모든 작업 제거."""
        # 처리 중이 아닌 작업만 제거
        self.tasks = [
            task for task in self.tasks
            if task.status == TaskStatus.PROCESSING
        ]
    
    def get_statistics(self) -> dict:
        """통계 정보."""
        total = len(self.tasks)
        pending = sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)
        processing = sum(1 for t in self.tasks if t.status == TaskStatus.PROCESSING)
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
        cancelled = sum(1 for t in self.tasks if t.status == TaskStatus.CANCELLED)
        
        return {
            'total': total,
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'cancelled': cancelled
        }
