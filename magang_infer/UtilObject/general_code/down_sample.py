import os
import datetime
import cv2
from pathlib import Path
from threading import Thread
import time
import sys
import logging

RAW_H = 2048
RAW_W = 4096
RATIO = 8
PATH112 = r'/diskb/server112/grab_img'
PATH113 = r'/diskb/server113/grab_img'


class LogFilter(logging.Filter):
    """Filters (lets through) all messages with level < LEVEL"""

    # http://stackoverflow.com/a/24956305/408556
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        # "<" instead of "<=": since logger.setLevel is inclusive, this should
        # be exclusive
        return record.levelno < self.level


MIN_LEVEL = logging.DEBUG
stdout_hdlr = logging.StreamHandler(sys.stdout)
stderr_hdlr = logging.StreamHandler(sys.stderr)
log_filter = LogFilter(logging.WARNING)
stdout_hdlr.addFilter(log_filter)
stdout_hdlr.setLevel(MIN_LEVEL)
stderr_hdlr.setLevel(max(MIN_LEVEL, logging.WARNING))
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y/%m/%d %I:%M:%S')
stdout_hdlr.setFormatter(formatter)
stderr_hdlr.setFormatter(formatter)

rootLogger = logging.getLogger()
rootLogger.addHandler(stdout_hdlr)
rootLogger.addHandler(stderr_hdlr)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def downsample(img, r):
    new_img = cv2.resize(img, (int(img.shape[1] / r), int(img.shape[0] / r)));
    return new_img


def CheckRawShape(img):
    if img.shape[0] == RAW_H and img.shape[1] == RAW_W:
        return True
    return False;


def task(data_path, target_year, target_month):
    for img_dir in Path(data_path).iterdir():
        try:
            time = datetime.datetime.strptime(img_dir.name, "%Y%m%d%H%M%S")
            if time.year == target_year and time.month == target_month:
                logger.info("Proccessing {}.".format(img_dir))
                for img_path in Path(img_dir).rglob("*.jpg"):
                    img = cv2.imread(str(img_path))
                    if CheckRawShape(img):
                        new_img = downsample(img, RATIO)
                        cv2.imwrite(str(img_path), new_img)
        except Exception as e:
            logger.error(e)
            continue


if __name__ == '__main__':
    once = False
    if once == True:
        time_now = datetime.datetime.now()
        if time_now.month == 1:
            target_time = time_now - datetime.timedelta(days=31)
            target_month = target_time.month
            target_year = target_time.year
        else:
            target_month = time_now.month - 1
            target_year = time_now.year
        p1 = Thread(target=task, args=(PATH112, target_year, target_month))
        p2 = Thread(target=task, args=(PATH113, target_year, target_month))
        p1.start()
        time.sleep(0.2)
        p2.start()
        p1.join()
        p2.join()

    while True:
        time_now = datetime.datetime.now()
        if time_now.month == 1:
            target_time = time_now - datetime.timedelta(days=31)
            target_month = target_time.month
            target_year = target_time.year
        else:
            target_month = time_now.month - 1
            target_year = time_now.year
        if time_now.day == 1:
            p1 = Thread(target=task, args=(PATH112, target_year, target_month))
            p2 = Thread(target=task, args=(PATH113, target_year, target_month))
            p1.start()
            p2.start()
        logger.info("Waiting for one day.")
        time.sleep(3600 * 24)