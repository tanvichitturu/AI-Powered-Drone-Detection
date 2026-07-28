import logging
import os
import sys
import queue
import atexit
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener

def setup_flight_logger(log_level: int = logging.INFO) -> logging.Logger:
    """
    Initializes a highly robust, non-blocking asynchronous logger.
    Offloads disk I/O to a background thread to prevent frame drops in the main loop.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "flight_telemetry.log")

    logger = logging.getLogger("DroneTracker")
    logger.setLevel(log_level)

    if not logger.handlers:
        
        # 1. The I/O Handlers (Owned exclusively by the Listener)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        file_handler.setLevel(log_level)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)

        formatter = logging.Formatter(
            fmt="[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 2. The Asynchronous Queue
        log_queue = queue.Queue(-1)
        
        # 3. The Listener (The Background Writer)
        # respect_handler_level ensures the console only gets WARNINGs, while the file gets INFO
        listener = QueueListener(
            log_queue, file_handler, console_handler, respect_handler_level=True
        )
        listener.start()

        # 4. Clean Shutdown Hook
        # Guarantees the queue flushes to the disk if the main script crashes or closes
        atexit.register(listener.stop)

        # 5. The Main Thread Handler
        # This is the ONLY handler attached to the actual logger
        queue_handler = QueueHandler(log_queue)
        logger.addHandler(queue_handler)

    return logger

# Global instance to be imported seamlessly
flight_log = setup_flight_logger()