"""Main entry point for AI Upscaler application."""
import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.ui.main_window import MainWindow


def setup_logging():
    """로깅 설정."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('ai_upscaler.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """메인 함수."""
    # 로깅 설정
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("="  * 60)
    logger.info("AI Upscaler - Starting")
    logger.info("=" * 60)
    
    # Qt 애플리케이션
    app = QApplication(sys.argv)
    app.setApplicationName("AI Upscaler")
    app.setOrganizationName("AI Upscaler")
    
    # High DPI 지원
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 메인 윈도우
    window = MainWindow()
    window.show()
    
    # 실행
    logger.info("Application started")
    exit_code = app.exec()
    
    logger.info("Application exited")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
