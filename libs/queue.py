# coding=utf-8

import web

from libs.mns.mns_client import MNSClient
from libs.mns.queue import Queue, Message
import settings
import utils


QUEUES = {}

class QueueManager(object):
    "阿里云MNS接口封装"
    def __init__(self, config):
        assert (config)

        self.config = config
        self._queues = {}
        # MNS 客户端
        self._mns_client = MNSClient(settings.MNS.URL, settings.MNS.ACCESS_KEY_ID, settings.MNS.ACCESS_KEY_SECRET)

    def __getattr__(self, name):
        if name in self._queues:
            return self._queues[name]

        queue_name = self.config.QUEUE.get(name.upper(), None)
        if queue_name:
            self._queues[name] = Queue(queue_name, self._mns_client, web.config.debug)
            return self._queues[name]

        raise AttributeError(name)

    def __getitem__(self, item):
        return self.__getattr__(item)

    def push(self, queue_name, entity, event, body, delayseconds = 0, priority = 8):
        "推送事件到队列中"
        p = [entity, event,]
        p.extend(body)

        m = Message(utils.json_dumps({ 'param': p }))
        m.set_delayseconds(delayseconds)
        m.set_priority(priority)

        return self[queue_name].send_message(m)

    def push_payback(self, order_id):
        "推送 payback 事件到队列中"
        self.push('pay', 'pay', 'payback', [order_id,], self.config.TIME.PAYBACK_DELAYSECONDS)

    def push_neworder(self, order_id, values):
        "推送 neworder 事件到队列中"
        values.order_id = order_id
        self.push('order', 'order', 'neworder', [values,], self.config.TIME.NEWORDER_DELAYSECONDS)

manager = QueueManager(settings.MNS)