#!/usr/bin/env python
# encoding: utf-8


#import sys
#sys.path.append('/'.join(__file__.split('/')[:-2]))

import web

import requests
from requests.exceptions import ConnectionError

import db
import settings
import utils

# === 队列类型 ===
# 签收邮件类型
SIGN_EMAIL = 1
# 结算邮件类型
SETTLE_EMAIL = 2
# 公告
NOTICE_EMAIL = 3
# 密码找回
PWD_EMAIL = 4
# 设置邮箱
SET_EMAIL = 5
# 修改邮箱
MODIFING_EMAIL = 6
# （取消）订阅
SUBSCRIBE_MAIL = 7

# === 队列优先级 ===
# 优先级高
PRIORITY_HIGH = 50
# 优先级中
PRIORITY_NORMAL = 20
# 优先级低
PRIORITY_LOW = 0

class Queue(object):
    @staticmethod
    def update(mq):
        "更新给定队列记录"
        return db.manager.master_core.update('queue_mail'
                , status = mq.status
                , message = mq.message if isinstance(mq.message, (str, unicode)) else utils.json_dumps(mq.message)
                , where = 'id = $id'
                , vars = mq)

    @staticmethod
    def mark_error(id, message):
        """
        标记队列错误
        @id as int, 队列内码
        @message as str, 消息
        """
        return db.manager.master_core.update('queue_mail'
                , status = 'T'
                , message = message
                , where = 'id = $id', vars = locals())

    @staticmethod
    def enqueue(uid, type, priority, body, status = 'E', mdb = None):
        "追加到队列"
        mdb = mdb or db.manager.master_core
        return mdb.insert('queue_mail'
                , user_id = uid, type = type, priority = priority
                , status = status, body = body)

    @staticmethod
    def pcompleted(type):
        """
        将给定类型的准备中队列状态(P)设置为准备完成(E)
        """
        return db.manager.master_core.update('queue_mail', status = 'E', where = 'type = $type', vars = locals())

    @staticmethod
    def penqueue(uid, type, priority, body, mdb = None):
        """
        追加一条准备状态的队列，同一个用户会不断的追加
        @body as dict, 追加队列的body必须时一个词典，格式如下
                { 'email': '接收的邮箱地址', 'values': '追加值，必须是一个列表' }
        """
        assert(isinstance(body, dict))
        assert('email' in body)
        assert('values' in body and isinstance(body['values'], list))
        # 获取用户处于准备中的队列记录
        q = Queue.get_user_status(uid, type, 'P', mdb = mdb)
        if q is None:
            # 初始化一条队列记录
            q = web.utils.storage(id = 0, user_id = uid
                    , type = type, priority = priority, status = 'P'
                    , body = body)
        else:
            q.body = utils.json_loads(q.body)
            q.body['email'] = body['email']
            q.body['values'].extend(body['values'])

        q.body = utils.json_dumps(q.body)
        # 覆盖更新之前的队列记录
        return Queue.replace(q, mdb = mdb)

    @staticmethod
    def replace(queue, mdb = None):
        "覆盖更新指定队列记录"
        mdb = mdb or db.manager.master_core
        if queue.id <= 0:
            return mdb.query("""
                    INSERT INTO queue_mail
                    SET user_id = $user_id, type = $type,
                        priority = $priority, status = $status,
                        body = $body;
                    """, vars = queue)
        else:
            return mdb.query("""
                    UPDATE queue_mail
                    SET user_id = $user_id, type = $type,
                        priority = $priority, status = $status,
                        body = $body
                    WHERE id = $id;
                    """, vars = queue)

    @staticmethod
    def get_user_status(uid, type, status, mdb = None):
        "获取一条给定用户给定类型给定状态的邮件队列数据"
        mdb = mdb or db.manager.slave_core
        rs = mdb.select('queue_mail', where = 'user_id = $uid AND type = $type AND status = $status', limit = 1, vars = locals())
        return rs[0] if rs else None

    @staticmethod
    def load_by_user(uid, type):
        """
        获取给定用户给定类型的邮件队列数据
        """
        return db.manager.slave_core.select('queue_mail', where = 'user_id = $uid AND type = $type', vars = locals())

    @staticmethod
    def dequeue():
        "获取一条队列记录"
        rs = db.manager.master_core.callproc("CALL dequeue_mail();")
        return rs[0] if rs else None

class APIError(Exception):
    pass

class SendcloudAPI(object):
    "Sendcloud发送接口类"
    def __init__(self, domain, api_key, api_user):
        "初始化接口类"
        self.domain = domain
        self.api_key = api_key
        self.api_user = api_user
        # 连接重试次数
        self._connection_reset_retry = 0

    def _make_url(self, api_method, fmt = 'json'):
        return 'http://sendcloud.sohu.com/webapi/%(api_method)s.%(fmt)s' % locals()

    def _call(self, http_method, api_method, **kwargs):
        """
        调用远程接口
        @http_method as str, 使用的HTTP方法 e.g. GET,POST,PUT,DELETE
        @api_method as str, 调用的接口方法  e.g. messages/domains
        @kwargs as dict, 接口方法所需参数
        """
        hm = getattr(requests, http_method, None)
        if hm is None:
            raise APIError('HTTP method was invalid.')

        kwargs['api_user'] = self.api_user
        kwargs['api_key'] = self.api_key

        while True:
            try:
                print utils.json_dumps(kwargs)
                return hm(self._make_url(api_method)
                        #, auth = ( 'api', self.api_key )
                        , data = kwargs
                    )
            except ConnectionError, ce:
                # 连接被重置
                if self._connection_reset_retry >= 3:
                    raise ce

                # 连接错误可以重试3次
                # 超过3次则抛出异常
                print '[SendcloudAPI]CONNECTION RESET RETRY %s/3' % self._connection_reset_retry
                self._connection_reset_retry += 1
                continue
            except Exception, e:
                # 超时异常，重试
                if 'timed out' in str(e):
                    print '[SendcloudAPI]TIME OUT RETRY'
                    continue

                raise e

    def _messages(self, **kwargs):
        "调用接口的 messages 方法"
        assert(kwargs['from'])
        assert(kwargs['fromname'])
        assert(kwargs['to'])
        assert(kwargs['subject'])
        if 'text' in kwargs and 'html' not in kwargs:
            kwargs['html'] = kwargs['text']
        assert('html' in kwargs and kwargs['html'])
        return self._call('post', 'mail.send', **kwargs)

    def notify(self, **kwargs):
        "使用 notify 发送邮件"
        kwargs['from']      = settings.SENDCLOUD.senders.notify.address
        kwargs['fromname']  = settings.SENDCLOUD.senders.notify.name
        return self._messages(**kwargs)

    def service(self, **kwargs):
        "使用 service 发送邮件"
        kwargs['from']      = settings.SENDCLOUD.senders.service.address
        kwargs['fromname']  = settings.SENDCLOUD.senders.service.name
        return self._messages(**kwargs)

    def list_add(self, mailist = 'all@maillist.sendcloud.org', **kwargs):
        """
        添加单条成员到给定的邮件列表中
        @address as str, 邮件列表地址
        """
        kwargs['subscribed'] = True
        kwargs['mail_list_addr'] = mailist
        kwargs['upsert'] = True
        return self._call('post', 'lists/%s/members' % mailist, **kwargs)

    def list_mset(self, mailist = 'all@maillist.sendcloud.org', **kwargs):
        """
        添加多条成员到给定的邮件列表中
        @address as str, 邮件列表地址
        """
        return False

class MailgunAPI(object):
    "Email发送接口基类"
    def __init__(self, domain, api_key):
        "初始化接口类"
        self.domain = domain
        self.api_key = api_key
        # 连接重试次数
        self._connection_reset_retry = 0

    def _make_url(self, postfix):
        return 'https://api.mailgun.net/v2/%s' % postfix

    def _call(self, http_method, api_method, **kwargs):
        """
        调用远程接口
        @http_method as str, 使用的HTTP方法 e.g. GET,POST,PUT,DELETE
        @api_method as str, 调用的接口方法  e.g. messages/domains
        @kwargs as dict, 接口方法所需参数
        """
        hm = getattr(requests, http_method, None)
        if hm is None:
            raise APIError('HTTP method was invalid.')

        while True:
            try:
                return hm(self._make_url(api_method)
                        , auth = ( 'api', self.api_key )
                        , data = kwargs
                    )
            except ConnectionError, ce:
                # 连接被重置
                if self._connection_reset_retry >= 3:
                    raise ce

                # 连接错误可以重试3次
                # 超过3次则抛出异常
                print '[MailgunAPI]CONNECTION RESET RETRY %s/3' % self._connection_reset_retry
                self._connection_reset_retry += 1
                continue
            except Exception, e:
                # 超时异常，重试
                if 'timed out' in str(e):
                    print '[MailgunAPI]TIME OUT RETRY'
                    continue

                raise e

    def _messages(self, **kwargs):
        "调用接口的 messages 方法"
        assert(kwargs['from'])
        assert(kwargs['to'])
        assert(kwargs['subject'])
        assert(kwargs['text'])
        return self._call('post', '%s/messages' % self.domain, **kwargs)

    def notify(self, **kwargs):
        "使用 notify@mail.yiju68.com 发送邮件"
        kwargs['from'] = settings.MAILGUN.senders.notify
        return self._messages(**kwargs)

    def service(self, **kwargs):
        "使用 service@mail.yiju68.com 发送邮件"
        kwargs['from'] = settings.MAILGUN.senders.service
        return self._messages(**kwargs)

    def list_add(self, mailist = 'members@mail.yiju68.com', **kwargs):
        """
        添加单条成员到给定的邮件列表中
        @address as str, 邮件列表地址
        """
        kwargs['subscribed'] = True
        return self._call('post', 'lists/%s/members' % mailist, **kwargs)

    def list_mset(self, mailist = 'members@mail.yiju68.com', **kwargs):
        """
        添加多条成员到给定的邮件列表中
        @address as str, 邮件列表地址
        """
        assert(kwargs['members'])
        kwargs['upsert'] = True
        return self._call('post', 'lists/%s/members.json' % mailist, **kwargs)

# email 实例
manager = MailgunAPI(settings.MAILGUN.domain, settings.MAILGUN.api_key)
#manager = SendcloudAPI(settings.SENDCLOUD.domain, settings.SENDCLOUD.api_key, settings.SENDCLOUD.api_user)

if __name__ == '__main__':
    #print manager.notify(to = 'members@mail.yiju68.com'
    #        , subject = u'uimeet 您好，您有5条订单于今日签收'
    #        , text = u'尊敬的 uimeet, 您好\n\n自昨日12时起至今日，有5条订单已签收，请登录平台查阅。')
    #print manager.list_add(
    #        address = '22788467@qq.com',
    #        name = u'阿蒙',
    #        description = 'Founder',
    #        vars = '{"age": 32}')
    import utils
    members = [
            {
                'address': 'uimeet <uimeet@gmail.com>',
                'vars': {'age':33}
            },
            {
                'name': 'mmslake',
                'address': 'mmslake@gmail.com',
                'vars': {'age': 27}
            }
        ]
    print manager.list_madd(
            members = utils.json_dumps(members))
