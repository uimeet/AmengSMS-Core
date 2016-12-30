# coding=utf-8

import fdfspyclient
import settings

class FastDFS(object):
    "FastDFS客户端"
    def __init__(self):
        print settings.APP_ROOT
        fdfspyclient.fdfs_init('/conf/fdfs-client.conf' % settings.APP_ROOT)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        fdfspyclient.fdfs_destroy()
        return False

    def __getattr__(self, item):
        handler = getattr(fdfspyclient, 'fdfs_%s' % item, None)
        if handler:
            return handler

        raise AttributeError(item)