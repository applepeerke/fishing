import logging
import os

from src.utils.functions import find_dirname_path

logger = logging.getLogger(__name__)

# Configure the logger
logger.setLevel(logging.INFO)  # Set base level to INFO

# Configure the logging handler (file output)
dirname = os.getenv('LOGGING_DIRNAME')
filename = os.getenv('LOGGING_FILENAME')
dir_path = find_dirname_path(dirname)
path = os.path.join(dir_path, filename) if dir_path else filename

handler = logging.FileHandler(path)
handler.setLevel(logging.INFO)   # Set level to INFO

# Set a custom formatter (optional)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)
