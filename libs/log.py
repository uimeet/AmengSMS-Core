# coding=utf-8

import logging
import logging.config

# 初始化日志对象
logging.config.fileConfig('%s/logger.conf' % '/'.join(__file__.split('/')[:-1]))


def debug(text, *args, **kwargs):
    return logging.debug(text, *args, **kwargs)

def log(text, *args, **kwargs):
    return logging.info(text, *args, **kwargs)

def error(text, *args, **kwargs):
    return logging.error(text, *args, **kwargs)

def warning(text, *args, **kwargs):
    return logging.warning(text, *args, **kwargs)