import logging
from pathlib import Path


def configure_logging(level=logging.INFO, log_dir='logs'):
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / 'modding-helper.log', encoding='utf-8')
        ]
    )
