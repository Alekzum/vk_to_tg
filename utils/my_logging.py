import logging


LEVEL = logging.INFO
FORMAT = '%(asctime)s - %(levelname)s (%(name)s) %(message)s'


logging.basicConfig(format=FORMAT, level=LEVEL)
logging.getLogger("httpx").setLevel(logging.WARNING)