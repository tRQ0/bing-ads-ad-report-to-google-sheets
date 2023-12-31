import logging
import os

def setup_logger(log_file="app.log"):
    if not os.path.exists(log_file):
       os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Configure the logging system
    logging.basicConfig(filename=log_file,
                        level=logging.INFO,
                        format="%(asctime)s - %(levelname)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")

def log_message(message, level=logging.INFO):
    # Log a message with the specified level
    logging.log(level, message)