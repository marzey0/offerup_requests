# app/utils/logg.py
import logging

def setup_logging(level=logging.INFO):
    """
    Настраивает корневой логгер приложения.
    Уровень DEBUG для собственного кода (app.*), WARNING для сторонних библиотек.
    Выводит в консоль и в файл debug.log.
    """
    # Создаём корневой логгер приложения
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG) # Корневой уровень DEBUG

    # Проверяем, не был ли уже установлен обработчик (во избежание дублирования в тестах)
    if logger.handlers:
        return logger

    # --- Формат ---
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Обработчик для файла ---
    file_handler = logging.FileHandler('data/debug.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG) # Файл содержит всё DEBUG и выше
    file_handler.setFormatter(formatter)

    # --- Обработчик для консоли ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # --- Добавляем обработчики ---
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # --- Подавляем уровень логирования для сторонних библиотек ---
    # Это предотвратит захламление логов их сообщениями DEBUG/INFO
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    # Если используются socks, возможно, тоже стоит подавить
    # logging.getLogger('socks').setLevel(logging.WARNING)

    return logger

# Глобальный экземпляр логгера, если нужно использовать напрямую
# logger = setup_logging()