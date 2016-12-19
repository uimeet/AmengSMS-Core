# coding=utf-8

"""
封装验证码逻辑
"""

import string
import random

class Vercode(object):
    def __init__(self):
        # 生成的验证码
        self._code = None

    def gen(self, length = 4, include_chars = string.digits):
        """
        生成指定的验证码
        """
        self._code = random.sample(include_chars, length)
        return self._code

    def __str__(self):
        return self._code