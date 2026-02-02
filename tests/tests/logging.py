import logging
import os
from sys import stderr, stdout

import loguru


_level = logging.DEBUG
_format = ''.join([
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | ',
    '<level>{level: <8}</level> | ',
    '<magenta>{process.name}</magenta>:<yellow>{thread.name}</yellow> | ',
    '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>'
])



def _opener(file: str | os.PathLike[str], flags: int) -> int:
    return os.open(file, flags, 0o777)



logger = loguru.logger
logger.remove() # Remove pre-configured STDERR hanlder



# STDOUT、STDERR 系列
# 1. DEBUG、INFO 輸出到 STDOUT。
logger.add(
    stdout,
    level=_level,
    format=_format,
    filter=lambda record: record.get('extra') == {} and record.get('level').no <= logging.INFO,
)

# 2. 警告與錯誤訊息輸出到 STDERR。
logger.add(stderr, level=logging.WARNING, format=_format)

# Log 檔系列
# 3. 全部資訊輸出到 log 檔。
logger.add(
    './logs/main-{time:YYYY-MM-DD}.log',
    level=_level,
    format=_format,
    filter=lambda record: record.get('extra') == {},
    rotation='10 MB',
    retention='10 days',
    compression='zip',
    opener=_opener,
)

# 4. 異常訊息輸出到 log 檔。
logger.add(
    './logs/error-{time:YYYY-MM-DD}.log',
    level=logging.WARNING,
    format=_format,
    rotation='10 MB',
    retention='10 days',
    compression='zip',
    opener=_opener,
)
