# coding=utf-8

from web.utils import storage
from core import utils
from core.libs import cache, db

# 比较器
Comparer = storage(
    # 开区间比较
    OpenInterval = lambda x, value: utils.floatval(x[0]) < value and utils.floatval(x[1]) > value,
    # 闭区间比较
    ClosedInterval = lambda x, value: utils.floatval(x[0]) <= value and utils.floatval(x[1]) >= value,
    # 左开右闭
    LeftOpenInterval = lambda x, value: utils.floatval(x[0]) < value and utils.floatval(x[1]) >= value,
    # 左闭右开
    LeftClosedInterval = lambda x, value: utils.floatval(x[0]) <= value and utils.floatval(x[1]) > value,
)

class DBConfig(storage):
    def __init__(self, table_name, items):
        self.raw_items = items
        self.table_name = table_name

        if items:
            super(DBConfig, self).__init__(**{ item.name : item.value for item in items })

    def __getattr__(self, name):
        return self.get(name, None)

    def bool(self, name):
        "获取给定配置的布尔型值"
        return bool(utils.intval(self.get(name)))

    def int(self, name, default = 0):
        "获取给定配置的整数值"
        return utils.intval(self.get(name), default)

    def float(self, name, default = 0.):
        "获取给定配置的浮点数值"
        return utils.floatval(self.get(name), default)

    def list(self, name, formatter = None, sep = ','):
        """
        获取一个列表值
        """
        value = self.get(name)
        if value:
            return [formatter(v) for v in value.split(sep)] if callable(formatter) else value.split(sep)

        return None

    def list_item(self, name, index = 0, func = None):
        "获取列表中的给定下标值"
        if index >= 0:
            l = self.list(name)
            if l and index < len(l):
                return func(l[index]) if callable(func) else l[index]

        return None

    def between(self, name, value, comparer = Comparer.LeftClosedInterval):
        """
        获取范围匹配值
        """
        # 用于在范围中匹配的值
        value = utils.floatval(value)
        # 获取对应的配置值
        v = self.get(name)
        if v:
            v = v.replace('\r', '\n').replace('@', '\n')
            for vs in v.split('\n'):
                vs = vs.strip().split('$')
                if len(vs) >= 2:
                    if comparer(vs, value):
                        if len(vs) == 3:
                            return [utils.intval(val) for val in vs[2].split(',')]
                        elif len(vs) == 2:
                            return True

        return None

    def flush(self):
        "清空缓存"
        cache.manager.delete('settings-%s' % self.table_name)

    @staticmethod
    def load(table_name):
        rs = DBConfig.db_load(table_name)
        return DBConfig(table_name, rs)

    @staticmethod
    @cache.cache('settings-%(table_name)s')
    def db_load(table_name):
        "加载给定表的配置"
        rs = db.manager.slave_core.select('%s_config' % table_name)
        return list(rs) if rs else None

    @staticmethod
    @cache.cache_delete('settings-%(table_name)s')
    def save(table_name, values):
        assert(isinstance(values, list))

        sets, names = [], []
        for v in values:
            v['value'] = v['value'].replace('$', '$$')
            sets.append("WHEN '%(name)s' THEN '%(value)s'" % v)

            names.append(v['name'])

        return db.manager.master_lottery.query("""
            UPDATE %s_config
            SET value = CASE name
                %s
                END
            WHERE name IN ('%s');
        """ % (table_name, ''.join(sets), "','".join(names)))

class Config(object):
    "设置管理器"
    def __getattr__(self, table_name):
        return DBConfig.load(table_name)

    def __setattr__(self, table_name, values):
        return DBConfig.save(table_name, values)

config = Config()

def load(table_name):
    "读取指定配置"
    return DBConfig.load(table_name)