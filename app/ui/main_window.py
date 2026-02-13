"""Main window for AI Upscaler application."""
import logging
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QSplitter, QTabWidget, QLabel,
    QProgressBar, QTextEdit, QGroupBox, QSpinBox,
    QComboBox, QCheckBox, QLineEdit, QListWidget, QListWidgetItem
)
from PySide6.QtWidgets import QMessageBox as QMB

from ..config.settings import SettingsManager
from ..config.presets import PresetManager
from ..core.task_queue import TaskQueue, UpscaleTask, TaskType
from ..core.worker import Worker
from ..core.models import ModelManager
from ..core.ffmpeg_handler import FFmpegHandler
from ..utils.file_utils import is_image, is_video, generate_output_filename
from ..utils.gpu_utils import detect_gpu, get_device

logger = logging.getLogger(__name__)


class FileListWidget(QListWidget):
    """드래그&드롭으로 파일을 받아 메인 윈도우로 전달하는 리스트."""
    files_dropped = Signal(list)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            if paths:
                self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MainWindow(QMainWindow):
    """메인 윈도우."""

    def __init__(self):
        super().__init__()

        # 매니저 초기화
        self.settings_manager = SettingsManager()
        self.preset_manager = PresetManager()
        self.model_manager = ModelManager()
        self.task_queue = TaskQueue()
        self.ffmpeg = FFmpegHandler()

        # GPU 감지
        self.gpu_available, self.gpu_info = detect_gpu()

        # Worker
        self.worker = None

        # UI 초기화
        self.init_ui()

        # 설정 로드
        self.load_settings()

        # FFmpeg 확인
        self.check_ffmpeg()

    def init_ui(self):
        """UI 초기화."""
        self.setWindowTitle("AI Upscaler - 이미지/동영상 업스케일러")
        self.setGeometry(100, 100, 1280, 720)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = self.create_file_list_panel()
        splitter.addWidget(left_panel)

        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

        self.statusBar().showMessage("준비됨")

    # ---------------------------
    # UI: Left Panel (File list)
    # ---------------------------
    def create_file_list_panel(self) -> QWidget:
        """파일 목록 패널."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        title = QLabel("<h3>파일 목록</h3>")
        layout.addWidget(title)

        # 드래그&드롭 가능한 리스트 위젯
        self.file_list = FileListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragEnabled(False)  # "드롭으로 추가"가 목적이므로 False가 안전
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list.files_dropped.connect(self.add_files_from_drop)
        layout.addWidget(self.file_list)

        button_layout = QHBoxLayout()

        add_btn = QPushButton("파일 추가")
        add_btn.clicked.connect(self.add_files)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("선택 제거")
        remove_btn.clicked.connect(self.remove_selected_files)
        button_layout.addWidget(remove_btn)

        clear_btn = QPushButton("전체 제거")
        clear_btn.clicked.connect(self.clear_files)
        button_layout.addWidget(clear_btn)

        layout.addLayout(button_layout)
        return panel

    # ---------------------------
    # UI: Right Panel (Tabs + Progress)
    # ---------------------------
    def create_right_panel(self) -> QWidget:
        """오른쪽 패널 (설정 + 진행률)."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        settings_tabs = self.create_settings_tabs()
        layout.addWidget(settings_tabs, stretch=2)

        progress_panel = self.create_progress_panel()
        layout.addWidget(progress_panel, stretch=1)

        return panel

    def create_settings_tabs(self) -> QTabWidget:
        """설정 탭."""
        tabs = QTabWidget()

        tabs.addTab(self.create_upscale_settings(), "업스케일")
        tabs.addTab(self.create_output_settings(), "출력")
        tabs.addTab(self.create_preset_settings(), "프리셋")

        return tabs

    def create_upscale_settings(self) -> QWidget:
        """업스케일 설정."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 스케일
        scale_group = QGroupBox("배율")
        scale_layout = QVBoxLayout()
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(1, 4)
        self.scale_spin.setValue(2)
        self.scale_spin.setSuffix("x")
        scale_layout.addWidget(self.scale_spin)
        scale_group.setLayout(scale_layout)
        layout.addWidget(scale_group)

        # 모델
        model_group = QGroupBox("AI 모델")
        model_layout = QVBoxLayout()
        self.model_combo = QComboBox()

        # ✅ (중요) 누락된 콤마 때문에 문자열 합쳐지는 버그 수정
        self.model_combo.addItems([
            "RealESRGAN_x2plus (2배속)",
            "RealESRGAN_x4plus (일반)",
            "RealESRNet_x4plus (노이즈 제거)",
            "RealESRGAN_x4plus_anime_6B (애니메이션)",
            "SwinIR_x4 (고품질 사진)",
            "Real_HAT_GAN_SRx4 (HAT 기본)",
            "Real_HAT_GAN_SRx4_sharper (HAT 선명)",
        ])
        model_layout.addWidget(self.model_combo)
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # GPU 사용
        gpu_group = QGroupBox("GPU")
        gpu_layout = QVBoxLayout()
        self.gpu_checkbox = QCheckBox(f"GPU 사용 ({self.gpu_info})")
        self.gpu_checkbox.setChecked(self.gpu_available)
        self.gpu_checkbox.setEnabled(self.gpu_available)
        gpu_layout.addWidget(self.gpu_checkbox)
        gpu_group.setLayout(gpu_layout)
        layout.addWidget(gpu_group)

        # 타일 크기
        tile_group = QGroupBox("타일 크기")
        tile_layout = QVBoxLayout()
        self.tile_combo = QComboBox()
        self.tile_combo.addItems(["256", "400", "512"])
        self.tile_combo.setCurrentText("512")
        tile_layout.addWidget(self.tile_combo)
        tile_layout.addWidget(QLabel("큰 값 = 빠름, 메모리 많이 사용"))
        tile_group.setLayout(tile_layout)
        layout.addWidget(tile_group)

        layout.addStretch()
        return widget

    def create_output_settings(self) -> QWidget:
        """출력 설정."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        dir_group = QGroupBox("출력 디렉토리")
        dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("출력 폴더 선택...")
        dir_layout.addWidget(self.output_dir_edit)

        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self.browse_output_dir)
        dir_layout.addWidget(browse_btn)

        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)

        image_group = QGroupBox("이미지 품질")
        image_layout = QVBoxLayout()

        jpg_layout = QHBoxLayout()
        jpg_layout.addWidget(QLabel("JPEG 품질:"))
        self.jpg_quality_spin = QSpinBox()
        self.jpg_quality_spin.setRange(1, 100)
        self.jpg_quality_spin.setValue(95)
        jpg_layout.addWidget(self.jpg_quality_spin)
        image_layout.addLayout(jpg_layout)

        png_layout = QHBoxLayout()
        png_layout.addWidget(QLabel("PNG 압축:"))
        self.png_compression_spin = QSpinBox()
        self.png_compression_spin.setRange(0, 9)
        self.png_compression_spin.setValue(6)
        png_layout.addWidget(self.png_compression_spin)
        image_layout.addLayout(png_layout)

        image_group.setLayout(image_layout)
        layout.addWidget(image_group)

        video_group = QGroupBox("동영상 설정")
        video_layout = QVBoxLayout()

        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("코덱:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["H.264 (호환성)", "H.265 (고품질)"])
        codec_layout.addWidget(self.codec_combo)
        video_layout.addLayout(codec_layout)

        crf_layout = QHBoxLayout()
        crf_layout.addWidget(QLabel("CRF (품질):"))
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(18)
        crf_layout.addWidget(self.crf_spin)
        crf_layout.addWidget(QLabel("낮을수록 고품질"))
        video_layout.addLayout(crf_layout)

        self.preserve_audio_checkbox = QCheckBox("오디오 보존")
        self.preserve_audio_checkbox.setChecked(True)
        video_layout.addWidget(self.preserve_audio_checkbox)

        video_group.setLayout(video_layout)
        layout.addWidget(video_group)

        layout.addStretch()
        return widget

    def create_preset_settings(self) -> QWidget:
        """프리셋 설정."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("프리셋:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.preset_manager.list())
        self.preset_combo.currentTextChanged.connect(self.load_preset)
        preset_layout.addWidget(self.preset_combo)
        layout.addLayout(preset_layout)

        self.preset_desc_label = QLabel()
        self.preset_desc_label.setWordWrap(True)
        layout.addWidget(self.preset_desc_label)

        btn_layout = QHBoxLayout()
        load_btn = QPushButton("프리셋 적용")
        load_btn.clicked.connect(lambda: self.load_preset(self.preset_combo.currentText()))
        btn_layout.addWidget(load_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()
        return widget

    def create_progress_panel(self) -> QWidget:
        """진행률 패널."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        title = QLabel("<h3>작업 진행</h3>")
        layout.addWidget(title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("대기 중...")
        layout.addWidget(self.status_label)

        log_group = QGroupBox("로그")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("시작")
        self.start_btn.clicked.connect(self.start_processing)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("중지")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        clear_log_btn = QPushButton("로그 지우기")
        clear_log_btn.clicked.connect(self.log_text.clear)
        button_layout.addWidget(clear_log_btn)

        layout.addLayout(button_layout)
        return panel

    # ---------------------------
    # File 관리
    # ---------------------------
    def add_files_from_drop(self, paths: list):
        """드래그&드롭으로 들어온 파일 추가."""
        for file_path in paths:
            self._try_add_file(file_path, via="드롭")

    def add_files(self):
        """파일 추가(파일 선택)."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "파일 선택",
            "",
            "이미지/동영상 (*.jpg *.jpeg *.png *.webp *.mp4 *.mkv *.mov *.avi);;모든 파일 (*.*)"
        )
        for file_path in files:
            self._try_add_file(file_path, via="선택")

    def _try_add_file(self, file_path: str, via: str = ""):
        """파일 유효성 검사 후 리스트에 추가 (중복 방지)."""
        if not file_path:
            return
        if not (is_image(file_path) or is_video(file_path)):
            self.add_log(f"스킵({via}): 지원하지 않는 형식 - {Path(file_path).name}")
            return

        # ✅ 중복 방지
        for i in range(self.file_list.count()):
            if self.file_list.item(i).text() == file_path:
                self.add_log(f"스킵({via}): 이미 추가됨 - {Path(file_path).name}")
                return

        self.file_list.addItem(QListWidgetItem(file_path))
        self.add_log(f"파일 추가({via}): {Path(file_path).name}")

    def remove_selected_files(self):
        """선택된 파일 제거."""
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def clear_files(self):
        """모든 파일 제거."""
        self.file_list.clear()

    def browse_output_dir(self):
        """출력 디렉토리 선택."""
        directory = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if directory:
            self.output_dir_edit.setText(directory)

    # ---------------------------
    # Settings 관리
    # ---------------------------
    def load_settings(self):
        """설정 로드."""
        settings = self.settings_manager.settings

        self.scale_spin.setValue(settings.scale_factor)
        self.output_dir_edit.setText(settings.output_directory)
        self.jpg_quality_spin.setValue(settings.jpg_quality)
        self.png_compression_spin.setValue(settings.png_compression)
        self.crf_spin.setValue(settings.video_crf)
        self.preserve_audio_checkbox.setChecked(settings.preserve_audio)
        self.gpu_checkbox.setChecked(settings.use_gpu and self.gpu_available)

        geom = settings.window_geometry
        self.resize(geom["width"], geom["height"])

    def save_settings(self):
        """설정 저장."""
        settings = self.settings_manager.settings

        settings.scale_factor = self.scale_spin.value()
        settings.output_directory = self.output_dir_edit.text()
        settings.jpg_quality = self.jpg_quality_spin.value()
        settings.png_compression = self.png_compression_spin.value()
        settings.video_crf = self.crf_spin.value()
        settings.preserve_audio = self.preserve_audio_checkbox.isChecked()
        settings.use_gpu = self.gpu_checkbox.isChecked()
        settings.window_geometry = {"width": self.width(), "height": self.height()}

        self.settings_manager.save()

    def load_preset(self, preset_name: str):
        """프리셋 로드."""
        preset = self.preset_manager.get(preset_name)
        if not preset:
            return

        self.scale_spin.setValue(preset.scale_factor)
        self.tile_combo.setCurrentText(str(preset.tile_size))
        self.jpg_quality_spin.setValue(preset.jpg_quality)
        self.crf_spin.setValue(preset.video_crf)

        self.preset_desc_label.setText(preset.description)
        self.add_log(f"프리셋 적용: {preset.name}")

    # ---------------------------
    # 작업 처리
    # ---------------------------
    def start_processing(self):
        """처리 시작."""
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "경고", "처리할 파일이 없습니다.")
            return

        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "경고", "출력 디렉토리를 선택하세요.")
            return

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # ✅ 재시작 시 이전 작업이 누적되지 않도록 큐 리셋
        self.task_queue = TaskQueue()

        self.create_tasks()
        self.start_worker()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.add_log("=" * 50)
        self.add_log("작업 시작")
        self.add_log("=" * 50)

    def create_tasks(self):
        """작업 생성."""
        output_dir = self.output_dir_edit.text().strip()
        scale = self.scale_spin.value()

        model_text = self.model_combo.currentText()

        # ✅ 모델 이름 매핑(표시 텍스트 기반)
        lower = model_text.lower()
        if "anime" in lower:
            model_name = "RealESRGAN_x4plus_anime_6B"
        elif "realesrnet" in lower:
            model_name = "RealESRNet_x4plus"
        elif "x2plus" in lower or "2배속" in model_text:
            model_name = "RealESRGAN_x2plus"
        elif "swinir" in lower:
            model_name = "SwinIR_x4"
        elif "sharper" in lower:
            model_name = "Real_HAT_GAN_SRx4_sharper"
        elif "hat" in lower:
            model_name = "Real_HAT_GAN_SRx4"
        else:
            model_name = "RealESRGAN_x4plus"

        codec = "h264" if "H.264" in self.codec_combo.currentText() else "h265"

        for i in range(self.file_list.count()):
            file_path = self.file_list.item(i).text()

            output_path = generate_output_filename(
                file_path,
                output_dir,
                preset_name="",
                scale=scale,
            )

            task_type = TaskType.IMAGE if is_image(file_path) else TaskType.VIDEO

            # ✅ task_id 빈값이면 이벤트/조회 매칭 깨질 확률 높음 → uuid 사용
            task = UpscaleTask(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                input_path=file_path,
                output_path=output_path,
                scale=scale,
                model_name=model_name,
                jpg_quality=self.jpg_quality_spin.value(),
                png_compression=self.png_compression_spin.value(),
                video_codec=codec,
                video_crf=self.crf_spin.value(),
                preserve_audio=self.preserve_audio_checkbox.isChecked(),
            )

            self.task_queue.add_task(task)

    def start_worker(self):
        """Worker 시작."""
        device = get_device(self.gpu_checkbox.isChecked())
        tile_size = int(self.tile_combo.currentText())

        # ✅ 기존 worker가 살아있으면 정리(안전)
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        self.worker = Worker(
            task_queue=self.task_queue,
            model_manager=self.model_manager,
            device=device,
            tile_size=tile_size,
        )

        self.worker.task_started.connect(self.on_task_started)
        self.worker.task_progress.connect(self.on_task_progress)
        self.worker.task_completed.connect(self.on_task_completed)
        self.worker.task_failed.connect(self.on_task_failed)
        self.worker.all_tasks_completed.connect(self.on_all_tasks_completed)

        self.worker.start()

    def stop_processing(self):
        """처리 중지."""
        if self.worker:
            self.worker.stop()
            self.add_log("중지 요청됨...")

    # ---------------------------
    # Worker 이벤트
    # ---------------------------
    def on_task_started(self, task_id: str):
        task = self.task_queue.get_task(task_id)
        if task:
            filename = Path(task.input_path).name
            self.add_log(f"시작: {filename}")
            self.status_label.setText(f"처리 중: {filename}")

    def on_task_progress(self, task_id: str, message: str, progress: float):
        # ✅ progress가 0~1로 올 수도, 0~100으로 올 수도 있어서 안전 처리
        if progress <= 1.0:
            progress = progress * 100.0
        self.progress_bar.setValue(max(0, min(100, int(progress))))
        self.status_label.setText(message)

    def on_task_completed(self, task_id: str):
        task = self.task_queue.get_task(task_id)
        if task:
            filename = Path(task.input_path).name
            self.add_log(f"완료: {filename}")

    def on_task_failed(self, task_id: str, error: str):
        task = self.task_queue.get_task(task_id)
        if task:
            filename = Path(task.input_path).name
            self.add_log(f"실패: {filename} - {error}")

    def on_all_tasks_completed(self):
        self.add_log("=" * 50)
        self.add_log("모든 작업 완료!")
        self.add_log("=" * 50)

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("완료")

        stats = self.task_queue.get_statistics()
        self.add_log(f"완료: {stats['completed']}, 실패: {stats['failed']}, 취소: {stats['cancelled']}")

        QMessageBox.information(
            self,
            "완료",
            f"처리 완료!\n완료: {stats['completed']}\n실패: {stats['failed']}"
        )

    # ---------------------------
    # 유틸
    # ---------------------------
    def add_log(self, message: str):
        self.log_text.append(message)
        logger.info(message)

    def check_ffmpeg(self):
        """FFmpeg 확인."""
        if not self.ffmpeg.is_available():
            QMessageBox.warning(
                self,
                "FFmpeg 없음",
                "FFmpeg가 설치되지 않았습니다.\n\n"
                "동영상 처리를 위해 FFmpeg가 필요합니다.\n"
                "https://ffmpeg.org 에서 다운로드하여 설치하세요."
            )
            self.add_log("경고: FFmpeg를 찾을 수 없습니다.")
        else:
            self.add_log("FFmpeg 감지됨")

    def closeEvent(self, event):
        """종료 이벤트."""
        self.save_settings()

        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "확인",
                "작업이 진행 중입니다. 종료하시겠습니까?",
                QMB.StandardButton.Yes | QMB.StandardButton.No,
            )

            if reply == QMB.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
