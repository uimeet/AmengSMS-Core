# coding=utf-8

import functools
import sys, base64
import os, time
import shutil
import web

try:
    import cPickle as pickle
except ImportError:
    import pickle
from web.utils import storage

import settings

if settings.CACHED.DRIVER == 'BMemcached':
    import bmemcached
elif settings.CACHED.DRIVER == 'Memcached':
    import memcache

from core import utils

class CachedManager(object):
    "缓存管理器"
    def __init__(self, driver, driver_options):
        self.driver = self._make_driver(driver, driver_options)

    def __getattr__(self, item):
        return getattr(self.driver, item)

    def _make_driver(self, driver, driver_options):
        "创建缓存驱动实例"
        driver_cls = getattr(sys.modules[__name__], '%sDriver' % driver, None)
        if driver_cls:
            return driver_cls(driver_options)

        return None

class Driver(object):
    "缓存驱动基类"
    def __init__(self, options):
        self.options = options

    def get(self, name):
        pass

    def get_json(self, name):
        pass

    def set(self, name, value, seconds = 0):
        return value

    def set_json(self, name, value, seconds = 0):
        return self.set(name, utils.json_dumps(value, utils.JsonEncoder), seconds)

    def get_set(self, name, expr, seconds = 0):
        "获取和设置值"
        value = self.get(name)
        if value:
            return value

        return self.set(name, expr(), seconds)

    def get_set_json(self, name, expr, seconds = 0):
        return self.get_set(name, expr, seconds)

    def getset_render(self, key_prefix, ids, render, seconds = 0):
        return render()

    def encode(self, cache_dict):
        """encodes cache dict as a string"""
        pickled = pickle.dumps(cache_dict)
        return base64.encodestring(pickled)

    def decode(self, cache_data):
        """decodes the data to get back the cache dict """
        pickled = base64.decodestring(cache_data)
        return pickle.loads(pickled)

class NoneDriver(Driver):
    "空驱动，不做任何实际的缓存"
    pass

class FileDriver(Driver):
    """
    本地文件缓存

    仅用于本地开发测试
    """
    def __init__(self, options):
        # if the storage root doesn't exists, create it.
        super(FileDriver, self).__init__(options)
        if not os.path.exists(options.ROOT):
            os.makedirs(
                    os.path.abspath(options.ROOT)
                    )
        self.root = options.ROOT

    def _get_path(self, key):
        if os.path.sep in key:
            raise ValueError, "Bad key: %s" % repr(key)
        return os.path.join(self.root, key)

    def __contains__(self, key):
        path = self._get_path(key)
        return os.path.exists(path)

    def __getitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            pickled = open(path).read()
            return self.decode(pickled)
        else:
            return None

    def __setitem__(self, key, value):
        path = self._get_path(key)
        pickled = self.encode(value)
        try:
            f = open(path, 'w')
            try:
                f.write(pickled)
            finally:
                f.close()
        except IOError:
            pass

    def __delitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)

    def get(self, name):
        value = self[name]
        if value:
            expire = utils.intval(value.get('time'))
            if expire and expire <= time.time():
                return None

            return self[name]['data']

        return None

    def get_json(self, name):
        data = self.get(name)
        return utils.json_loads(data) if data else None

    def set(self, name, value, seconds = 0):
        value = {
            'data': value
        }
        if seconds > 0:
            value['time'] = time.time() + seconds

        self[name] = value
        return value

    def set_json(self, name, value, seconds = 0):
        return self.set(name, utils.json_dumps(value, utils.JsonEncoder), seconds)

    def getset_render(self, key_prefix, ids, render, seconds = 0):
        "设置模板渲染器缓存"
        if settings.CACHED.ENABLE_PAGE_CACHED:
            key = '%s-%s' % (key_prefix.upper(), '-'.join([str(i) for i in ids]),)
            content = self.get(key)
            if content:
                return utils.base64_decode(content)

            content = str(render())

            self.set(key, utils.base64_encode(content), seconds)
            return content

        return render()

    def delete(self, name):
        path = self._get_path(name)
        if os.path.exists(path):
            os.remove(path)

    def flush_all(self, seconds = 0):
        shutil.rmtree(self.root)

class MemcachedDriver(Driver):
    def __init__(self, options):
        super(MemcachedDriver, self).__init__(options)

        self.hosts      = self.options.HOSTS
        self.client     = memcache.Client(self.hosts)

    def get(self, name):
        return self.client.get(name)

    def get_json(self, name):
        return utils.json_loads(self.client.get(name))

    def set(self, name, value, seconds = 0):
        self.client.set(name, value, seconds)
        return value

    def set_json(self, name, value, seconds = 0):
        return self.set(name, utils.json_dumps(value, utils.JsonEncoder), seconds)

    def getset_render(self, key_prefix, ids, render, seconds = 0):
        "设置模板渲染器缓存"
        if settings.CACHED.ENABLE_PAGE_CACHED:
            key = '%s-%s' % (key_prefix.upper(), '-'.join([str(i) for i in ids]),)
            content = self.get(key)
            if content:
                return utils.base64_decode(content)

            content = str(render())

            self.set(key, utils.base64_encode(content), seconds)
            return content

        return render()

    def delete(self, name, cas = 0):
        return self.client.delete(name, cas)

    def flush_all(self, seconds = 0):
        return self.client.flush_all(seconds)

class BMemcachedDriver(Driver):
    def __init__(self, options):
        super(BMemcachedDriver, self).__init__(options)

        self.hosts      = self.options.HOSTS
        self.sasl_name  = self.options.SASL_NAME
        self.sasl_pwd   = self.options.SASL_PASSWORD
        self.client     = bmemcached.Client(self.hosts, self.sasl_name, self.sasl_pwd)

    def get(self, name):
        return self.client.get(name)

    def get_json(self, name):
        return utils.json_loads(self.client.get(name))

    def set(self, name, value, seconds = 0):
        self.client.set(name, value, seconds)
        return value

    def set_json(self, name, value, seconds = 0):
        return self.set(name, utils.json_dumps(value, utils.JsonEncoder), seconds)

    def getset_render(self, key_prefix, ids, render, seconds = 0):
        "设置模板渲染器缓存"
        if settings.CACHED.ENABLE_PAGE_CACHED:
            key = '%s-%s' % (key_prefix.upper(), '-'.join([str(i) for i in ids]),)
            content = self.get(key)
            if content:
                return utils.base64_decode(content)

            content = str(render())

            self.set(key, utils.base64_encode(content), seconds)
            return content

        return render()

    def delete(self, name, cas = 0):
        return self.client.delete(name, cas)

    def flush_all(self, seconds = 0):
        return self.client.flush_all(seconds)

manager = CachedManager(settings.CACHED.DRIVER, settings.CACHED.OPTIONS)

# 缓存装饰器
def cache(key_fmt = None, seconds = 600):
    """
    缓存装饰器
    @key_prefix str 缓存键的前缀，如不提供则为方法名
    @seconds int 缓存的秒数
    """
    def proxy(func):
        def wrapper(* args, ** kwargs):
            # Web参数
            values = {}
            if utils.is_http():
                values.update(web.input())
            # 函数参数
            if args or kwargs:
                values.update(utils.arrange_args(func, *args, **kwargs))

            key = key_fmt
            if key:
                if '%(' in key:
                    key = key % values

            if not key:
                key = func.__name__

            funcwrapper = func

            data = manager.get(key)
            if data is None:
                if utils.is_method(funcwrapper):
                    funcwrapper = functools.partial(funcwrapper, args.pop(0))

                data = funcwrapper(*args, **kwargs)
                if data is not None:
                    manager.set(key, data, seconds = seconds)

            return data
        return wrapper
    return proxy

def cache_delete(keys):
    """
    缓存删除装饰器
    @keys tuple/list 要删除的缓存键，可以坚守 fmt 字符串，会使用方法的参数自动替换
    """
    def proxy(func):
        def wrapper(*args, **kwargs):
            funcwrapper = func
            if utils.is_method(funcwrapper):
                funcwrapper = functools.partial(funcwrapper, args.pop(0))

            data = funcwrapper(*args, **kwargs)
            if not isinstance(keys, (tuple, list)):
                keyfmts = [keys]
            else:
                keyfmts = keys

            # 是否清除缓存
            if isinstance(data, (dict, storage)) and data.get('_cache_deleted', True) is False:
                return data

            # Web参数
            values = {}
            if utils.is_http():
                values.update(web.input())
            # 函数参数
            if args or kwargs:
                values.update(utils.arrange_args(func, *args, **kwargs))

            # 删除缓存
            for keyfmt in keyfmts:
                key = keyfmt
                if '%(' in key:
                    # 参数有效尝试替换key中的
                    if values:
                        key %= values

                manager.delete(key)

            return data
        return wrapper
    return proxy