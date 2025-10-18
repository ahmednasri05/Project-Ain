"""
Logging configuration for Crime Monitoring AI.
"""

import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = "crime_monitoring.log"):
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers
    logging.getLogger('openai').setLevel(logging.WARNING)  # Reduce OpenAI SDK noise
    logging.getLogger('httpx').setLevel(logging.WARNING)   # Reduce HTTP noise
    logging.getLogger('google').setLevel(logging.WARNING)  # Reduce Google SDK noise
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")

