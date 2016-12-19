# coding=utf-8

"""
枚举值基类
"""


from web.utils import storage
from core import utils

class Enum(storage):
    # 未知项
    Unknown = storage(value = -1, text = u'未知', tag = 'unknown')

    def find(self, value, default = None):
        "查找指定值的枚举项"
        return next(
            iter(v for v in self.values() if v.value == value),
            default or self.Unknown)

    def exists(self, item):
        "给定枚举项是否存在"
        return any(v for v in self.values() if v == item)

    def all(self, values):
        """
        查找所有给定值的枚举项
        :param values: list或str, [1,2,3]或'1,2,3'都支持
        :return:
        """
        if isinstance(values, (str, unicode)):
            values = [utils.intval(v) for v in values.split(',')]

        result = []
        for v in values:
            item = self.find(v)
            if item != self.Unknown:
                result.append(item)

        return result

    def all_text(self, values, sep = ','):
        """
        查找并获取所有给定值的枚举项的text值
        :param values:
        :param sep: 间隔符, 如果为None则直接范围list
        :return:
        """
        items = self.all(values)
        if items:
            result = [item.text for item in items]
            return sep.join(result) if sep else result

        return None