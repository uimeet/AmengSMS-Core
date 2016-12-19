# coding=utf-8

"""
supervisor 的 XML-RPC 接口
"""

import xmlrpclib


class Server(object):
    "Supervisor 的服务端对象"

    def __init__(self, host, username, passwd, suffix='RPC2'):
        assert (host)

        self.host = host
        self._inst = xmlrpclib.Server('http://%(username)s:%(passwd)s@%(host)s/%(suffix)s' % locals())

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __getattr__(self, item):
        methods = ('system', item)
        if '_' in item:
            methods = item.split('_')

        target = self._inst
        for m in methods:
            target = getattr(target, m, None)
            if target is None:
                raise Exception('Target:%s not found.' % m)

        return target


class ServerManager(object):
    def __init__(self, hosts, suffix='RPC2'):
        assert (isinstance(hosts, (tuple, list)))
        self.hosts = hosts
        self._insts = {
            host['host']:
                Server(host['host'], host['user'], host['passwd'], host.get('suffix', 'RPC2')) for host in self.hosts
        }

    def __getitem__(self, item):
        if isinstance(item, (int, long)):
            return self._insts[self.hosts[item]['host']]
        elif isinstance(item, (str, unicode)):
            return self._insts.get(item, None)

        return None

    def execute(self, command, *kargs):
        results = {}
        for host, inst in self._insts.iteritems():
            results[host] = inst[command](*kargs)

        return results


if __name__ == '__main__':
    sm = ServerManager([{'host': '127.0.0.1:7002', 'user': 'uimeet', 'passwd': 'yan923', 'suffix': 'RPC2'}, ])
    print sm.execute('supervisor_getState')
    #print sm[0].supervisor_getAllProcessInfo()
    #print sm[0].supervisor_getProcessInfo('uwsgi:uwsgi_001')
