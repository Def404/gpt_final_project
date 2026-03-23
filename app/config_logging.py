import logging
import os
from pythonjsonlogger import json
from logging.handlers import TimedRotatingFileHandler


# Путь к логам
log_path = os.path.join(os.getcwd(), "logs")
os.makedirs(log_path, exist_ok=True)
log_file = os.path.join(log_path, "app.log")

# Создаём хендлер для файла
file_handler = TimedRotatingFileHandler(
    log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s %(funcName)s %(message)s'
    )
)

# Хендлер для консоли
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(
    json.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(funcName)s %(message)s'
    )
)

# Базовая конфигурация
logging.basicConfig(
    level=logging.DEBUG,  # Важно, чтобы пропускать DEBUG в файл
    handlers=[
        file_handler,
        console_handler,
    ]
)


# Функция для получения именованного логгера
def get_logger(name):
    return logging.getLogger(name)
