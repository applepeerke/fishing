import logging
logger = logging.getLogger(__name__)

# Configure the logger
logger.setLevel(logging.WARNING)  # Set level to WARNING

# Configure the logging handler (e.g., console output)
handler = logging.FileHandler('fishing.log')
handler.setLevel(logging.WARNING)

# Set a custom formatter (optional)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)
