import logging

def setup_logging():
    """
    Configure logging settings for FactLite framework.
    
    This function sets up a global logging configuration with:
    - INFO level logging
    - Custom format including timestamp and module name
    - Console handler for output
    """
    # Create logger with module name
    logger = logging.getLogger('FactLite')
    logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handler to logger if not already added
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger

# Create global logger instance
logger = setup_logging()