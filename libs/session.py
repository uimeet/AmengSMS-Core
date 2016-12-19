#!/usr/bin/env python
# encoding: utf-8

import web
import cache

class Session(web.session.Session):
    def _processor(self, handler):
        # 当访问的路径是 /env 时不做任何处理
        # SLB 中是通过这个路径来进行健康检查的
        # 健康检查时无cookie状态，会造成系统不断的新建session记录
        if web.ctx.env.get('REQUEST_URI', None) != '/env':
            return super(Session, self)._processor(handler)

        return handler()

    def expired(self):
        self._killed = True
        self._save()
        # 这里这里将 session_id 清空
        # 是因为，如果不抛出异常的情况下，程序将继续执行
        # 因为数据已经过期，已有的session_id将对应的数据将不存在
        # 那么在 _load 方法中将会异常，这里设置为None
        # 在_load方法中重新生成session_id
        self.session_id = None
        if self._config.expired_message:
            raise web.session.SessionExpired(self._config.expired_message)

class MemcachedStore(web.session.Store):
    """Store for saving a session in memcached
    Needs a table with the following columns:

        session_id CHAR(128) UNIQUE NOT NULL,
        atime DATETIME NOT NULL default current_timestamp,
        data TEXT
    """
    def __init__(self, cache_mgr):
        self.cache_mgr = cache_mgr

    def __contains__(self, key):
        data = self.cache_mgr.get(key)
        return bool(data)

    def __getitem__(self, key):
        return self.cache_mgr.get(key)

    def __setitem__(self, key, value):
        return self.cache_mgr.set(key, value, web.config.session_parameters['timeout'])

    def __delitem__(self, key):
        self.cache_mgr.delete(key)

    def cleanup(self, timeout):
        return True

def session_init(app):
    "初始化session"
    session = web.config.get('_session')
    if session is None:
        session = Session(app, MemcachedStore(cache_mgr=cache.manager))
        web.config._session = session
    else:
        session = web.config._session
    return session

web.config.session_parameters['cookie_name'] = 'AM_SESSION_ID'
web.config.session_parameters['cookie_domain'] = None
web.config.session_parameters['cookie_path'] = '/'
web.config.session_parameters['timeout'] = 15 * 60
web.config.session_parameters['ignore_expiry'] = True
web.config.session_parameters['ignore_change_ip'] = True
web.config.session_parameters['secret_key'] = '!FuckYouSister!'
web.config.session_parameters['expired_message'] = None
