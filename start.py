import runtime_platform
import logging


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Запуск основного скрипта...")
    try:
        runtime_platform.check_platform()
    except KeyboardInterrupt:
        logger.info("Скрипт остановлен.")
    
    # exit(0)
