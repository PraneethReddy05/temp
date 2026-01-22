import yaml
import logging
import sys
import functools
from typing import Dict, Any

def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config file: {e}")
        sys.exit(1)

# def setup_logging(level: str = "INFO") -> None:
#     """
#     Configure global logging settings.
#     """
#     numeric_level = getattr(logging, level.upper(), None)
#     if not isinstance(numeric_level, int):
#         print(f"Invalid log level: {level}. Defaulting to INFO.")
#         numeric_level = logging.INFO

#     logging.basicConfig(
#         level=numeric_level,
#         format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S',
#         handlers=[
#             logging.StreamHandler(sys.stdout)
#             # You can add FileHandler here if needed
#         ]
    # )

def setup_logging(level: str = "INFO") -> None:
    """
    Configure global logging to show in BOTH terminal and code handlers.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers to prevent duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 1. CREATE TERMINAL HANDLER (Standard Output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create a nice format for the terminal
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add it to the root logger
    root_logger.addHandler(console_handler)
    
    logging.info(f"Logging initialized at {level} level. Terminal output active.")

# --- NEW CACHING DECORATOR ---
# This provides a simple, in-memory cache for our queries.
# The `lru_cache` will store the results of the `handle_user_query` function.
# If the same query is asked again, it will return the cached result
# without running any agents or LLM calls.
def memoize_query(func):
    """
    A decorator to cache query results using functools.lru_cache.
    Since lru_cache expects hashable arguments, and our Controller methods
    might take just strings (hashable), this simple wrapper works well.
    """
    @functools.lru_cache(maxsize=100)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper