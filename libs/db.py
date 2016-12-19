# coding=utf-8

import random
import web
from web.utils import storage
import settings

class RelationTransaction(web.db.Transaction):
    def __init__(self, ctx, relation_tran = None):
        web.db.Transaction.__init__(self, ctx)
        self.relation_tran = relation_tran

    def __exit__(self, exctype, excvalue, traceback):
        # 是否设置关联事务
        if self.relation_tran:
            if exctype is not None:
                self.relation_tran.rollback()
            else:
                self.relation_tran.commit()

        web.db.Transaction.__exit__(self, exctype, excvalue, traceback)

    def rollback(self):
        if self.relation_tran:
            self.relation_tran.rollback()

        web.db.Transaction.rollback(self)

    def commit(self):
        if self.relation_tran:
            self.relation_tran.commit()

        web.db.Transaction.commit(self)

class DBError(Exception):
    pass

class ConnectionError(DBError):
    pass

class MasterNotFoundError(ConnectionError):
    pass

class SlaveNotFoundError(ConnectionError):
    pass

class ProcDB(web.db.MySQLDB):
    def callproc(self, sql_query, vars=None, processed=False, _test=False):
        "调用给定存储过程"
        if vars is None: vars = {}

        if not processed and not isinstance(sql_query, web.db.SQLQuery):
            sql_query = web.db.reparam(sql_query, vars)

        if _test: return sql_query

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, sql_query)

        if db_cursor.description:
            names = [x[0] for x in db_cursor.description]
            def iterwrapper():
                row = db_cursor.fetchone()
                while row:
                    yield storage(dict(zip(names, row)))
                    row = db_cursor.fetchone()
            out = web.utils.iterbetter(iterwrapper())
            out.__len__ = lambda: int(db_cursor.rowcount)
            out.list = lambda: [storage(dict(zip(names, x))) \
                               for x in db_cursor.fetchall()]
            out = list(out)
            # 因为是调用存储过程，这里必须关闭游标否则一直报错
            db_cursor.close()
        else:
            out = db_cursor.rowcount

        if not self.ctx.transactions:
            self.ctx.commit()
        return out

    def transaction(self, relation_tran = None):
        "开启一个事务，并可设置一个关联事务"
        return RelationTransaction(self.ctx, relation_tran)

# 注册数据库，覆盖原来对mysql的注册
web.db.register_database('mysql', ProcDB)

class DBManager(object):
    def __init__(self, dbsettings):
        assert(dbsettings)
        self._db = {}
        self.dbsettings = dbsettings
        self.slave_rr_counter = None

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __getattr__(self, name):
        if '_' in name:
            attrs = name.split('_')
            if len(attrs) == 2:
                func = getattr(self, attrs[0], None)
                if func and callable(func):
                    return func(attrs[1])

        raise AttributeError(name);

    def _dbget(self, setting):
        """
        从缓存获取一个数据库实例
        @setting as dict, 一个关于数据库的配置
        """
        dbkey = ','.join(['%s=%s' % (k, v) for k, v in setting.iteritems()])
        if web.config.debug:
            print '_dbget: dbkey', dbkey
        if dbkey not in self._db:
            self._db[dbkey] = web.database(dbn = 'mysql', ** setting)
            if web.config.debug:
                print '_dbget[create]: dbkey', dbkey

        return self._db[dbkey]

    def discover_master(self, service_name):
        """
        找到给定 service_name 的 master 配置
        """
        msettings = self.dbsettings.get(service_name, None)
        if msettings:
            return msettings['master']

        raise MasterNotFoundError('No master found for %r' % (service_name,))

    def discover_slaves(self, service_name):
        """
        找到给定 service_name 的 slaves 配置
        """
        ssettings = self.dbsettings.get(service_name, None)
        if ssettings:
            return ssettings.get('slaves', [])

        return []

    def rotate_slaves(self, service_name):
        "轮询slave"
        slaves = self.discover_slaves(service_name)
        if slaves:
            if self.slave_rr_counter is None:
                self.slave_rr_counter = random.randint(0, len(slaves) - 1)
            for _ in xrange(len(slaves)):
                self.slave_rr_counter = (
                        self.slave_rr_counter + 1) % len(slaves)
                slave = slaves[self.slave_rr_counter]
                return slave
        try:
            return self.discover_master(service_name)
        except MasterNotFoundError:
            pass

        raise SlaveNotFoundError('No slave found for %r' % (service_name,))

    def master(self, service_name):
        """
        获取一个 service_name 的 master 数据库实例
        """
        master_setting = self.discover_master(service_name)
        return self._dbget(master_setting)

    def slave(self, service_name):
        """
        获取一个 service_name 的 slave 数据库实例
        """
        slave_setting = self.rotate_slaves(service_name)
        return self._dbget(slave_setting)

manager = DBManager(settings.DATABASES)

class Connection(object):
    '''数据库对象'''
    def __init__(self):
        self.dbs = {}

    '''
        connection.default 的方式获取数据库操作对象
    '''
    def __getattr__(self, key):
        return manager.master(key)

    def __getitem__(self, key):
        return self.__getattr__(key)

    def dispose(self):
        if self.dbs:
            self.dbs.clear()

connection = Connection()

if __name__ == '__main__':
    print manager.slave_core
