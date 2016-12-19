# coding=utf-8

from web.utils import storage

from core.libs import db
from core.libs.supervisor import Server

import enums

class Host(storage):
    "主机实体"
    def __init__(self, **kwargs):
        super(Host, self).__init__(**kwargs)

        self.status = kwargs.get('status', enums.SupervisorHost.Status.Stopped)
        if isinstance(self.status, (int, long)):
            self.status = enums.SupervisorHost.Status.find(self.status)

        self._server = None

    def get_server(self):
        if self._server is None:
            self._server = Server(self.host, self.user, self.passwd, self.suffix)

        return self._server

    def get_processes(self):
        """
        获取给主机下所有启动的进程
        :return:
        """
        procs = self.get_server().supervisor_getAllProcessInfo()
        return procs


class HostDAL(object):
    "任务主机相关接口"
    @staticmethod
    def find(ip, port):
        "获取给定任务主机记录"
        host = '%s:%s' % (ip, port)

        rs = db.manager.slave_core.select('supervisor_host', where='host = $host', vars=locals())
        return rs[0] if rs else None

    @staticmethod
    def update_status(host_id, status, status_text):
        "更新主机的运行状态"
        return db.manager.master_core.update('supervisor_host'
                                                , run_status=status
                                                , run_status_text=status_text
                                                , where='id = $host_id'
                                                , vars=locals())

    @staticmethod
    def find_all():
        "获取所有主机记录"
        return db.manager.slave_core.select('supervisor_host')

    @staticmethod
    def find_by_id(host_id):
        "获取给定主机记录"
        rs = db.manager.slave_core.select('supervisor_host', where = 'id = $host_id', vars = locals())
        return Host(**rs[0]) if rs else None


class ProcessDAL(object):
    "任务进程相关接口"
    @staticmethod
    def find_by_host_id(host_id):
        "获取给定主机要启动的进程记录"
        return db.manager.slave_core.select('supervisor_proc', where='host_id = $host_id', vars=locals())


    @staticmethod
    def find_by_host_id_procode(host_id, proc_code):
        "获取给定主机给定进程记录"
        rs = db.manager.slave_core.select('supervisor_proc', where='host_id = $host_id AND code = $proc_code',
                                             vars=locals())
        return rs[0] if rs else None

    @staticmethod
    def find_by_proccode(proc_code):
        "获取给定进程码的所有记录"
        rs = db.manager.slave_core.select('supervisor_proc', where='code = $proc_code AND status IN (1, 2)',
                                             order='id ASC', vars=locals())
        return rs

