# coding=utf-8

import threadpool

import http
from core import utils

import settings

class iComet(object):
    "iComet 客户端"
    def __init__(self, host, admin_port, user_port):
        """
        初始化 iComet 客户端实例

        @host str 主机地址
        @admin_port int 管理端口
        @user_port int 用户端口
        """
        self.host = host
        self.admin_port = admin_port
        self.user_port = user_port

        self.admin_url = 'http://%(host)s%(admin_port)s/ic-adm/' % {
            'host': self.host,
            'admin_port': ':%s' % self.admin_port if self.admin_port != 80 else '',
        }
        self.user_url = 'http://%(host)s:%(user_port)s/ic/' % {
            'host': self.host,
            'user_port': ':%s' % self.user_port if self.user_port != 80 else '',
        }

    def sign(self, channel, expires = 60):
        """
        创建并获取频道口令
        """
        resp = http.GET('%ssign?cname=%s&expires=%s' % (self.admin_url, channel, expires,))
        return resp.json()

    def push(self, channel, data):
        "推送消息"
        try:
            resp = http.GET('%spush?cname=%s&content=%s' % (self.admin_url, channel, utils.urlencode(data),))
            return resp.json()
        except:
            return False

    def broadcast(self, data, delay = 0):
        "广播一条消息"
        if not isinstance(data, (str, unicode)):
            data = utils.json_dumps(data)

        if delay > 0:
            utils.sleep(delay)

        try:
            resp = http.GET('%sbroadcast?content=%s' % (self.admin_url, utils.urlencode(data)))
            return resp.text.strip().lower() == 'ok'
        except:
            return False

    def broadcast_async(self, data, delay = 0):
        "异步广播一条消息"
        pool = threadpool.ThreadPool(1)
        reqs = threadpool.makeRequests(lambda x: self.broadcast(x, delay = delay), [data], self._print_result)
        [pool.putRequest(req) for req in reqs]
        pool.wait()
        return True

    def user(self, user_id, data):
        """
        向给定用户推送消息
        :param user_id: 用户内码
        :param data: 数据
        :return:
        """
        return self.push('bn_%s' % utils.id_to_hex(user_id), data)

    def user_async(self, user_id, data = None):
        """
        向给定用户异步推送消息
        :param user_id: 用户内码
        :param data: 数据
        :return:
        """
        return self.push_async([{
            'channel': 'bn_%s' % utils.id_to_hex(user_id),
            'data': utils.json_dumps(data),
        }])

    def push_async(self, notifies):
        """
        异步推送消息
        :param notifies: 推送的通知数据
        :return:
        """
        pool = threadpool.ThreadPool(len(notifies))
        reqs = threadpool.makeRequests(lambda x: self.push(x['channel'], x['data']), notifies, self._print_result)
        [pool.putRequest(req) for req in reqs]
        pool.wait()
        return True

    def _print_result(self, request, n):
        """
        打印推送通知的结果
        :param notify:
        :return:
        """
        print '%s - %s' % (request.requestID, n)

    def sub(self, channel):
        "订阅给定频道"
        pass

client = iComet(settings.COMET.HOST, settings.COMET.ADMIN_PORT, settings.COMET.USER_PORT)