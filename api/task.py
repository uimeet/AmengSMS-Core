# coding=utf-8

import traceback
import web
from web.utils import storage

from core import utils
from core.libs import db, log

import enums

# 所有已注册任务索引
_registered_handlers = {}

def register_taskhandler(type):
    "用于注册任务处理器的装饰器"
    def register(f):
        types = type
        if not isinstance(types, (list, tuple)):
            types = [types]

        for t in types:
            _registered_handlers[t.value] = f
        return f
    return register

class TaskHandler(object):
    "任务处理者"
    def __init__(self, task):
        self.message = []
        self.necessary = True
        self.task = task
        self.task.handler = self
        # 是否忽略错误
        self.ignore_error = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and isinstance(exc_val, Exception):
            self.mark_error(traceback.format_exception(exc_type, exc_val, exc_tb))

        if self.has_error:
            self.error(self.message[-1])
        else:
            self.debug(utils.json_dumps(self.message))

        # 记录任务日志
        mdb = db.manager.master_core
        with mdb.transaction():
            self.task.save(mdb = mdb)
            self.save_task_logs(mdb = mdb)

        return self.ignore_error

    def debug(self, text):
        return log.debug(u'[%s]%s' % (self.task.type.tag, text))

    def warning(self, text):
        return log.warning(u'[%s]%s' % (self.task.type.tag, text))

    def log(self, text):
        return log.log(u'[%s]%s' % (self.task.type.tag, text))

    def error(self, text):
        return log.error(u'[%s]%s' % (self.task.type.tag, text))

    def execute(self, **kwargs):
        pass

    def save_task_logs(self, mdb = None):
        """
        保存任务执行日志
        :param mdb:
        :return:
        """
        if self.message:
            return TaskDAL.add_execlog(self.task, self.message)

        return False

    @property
    def has_error(self):
        "执行是否包含错误"
        return self.task.status == enums.Task.Status.Failure

    def message_append(self, key, message):
        self.message.append({
            'type': key,
            'message': message,
            'time': utils.now(fmt = '%Y-%m-%d %H:%M:%S'),
        })

    def mark_delay(self, message, seconds = 5):
        """
        标记一次延迟激活状态
        :param message: 状态备注
        :param seconds: 延迟的秒数
        :return:
        """
        self.task.status = enums.Task.Status.Waiting
        self.task.status_text = message
        self.task.executed = True
        self.message_append('info', message)
        self.necessary = False
        # 下次激活时间
        self.task.active_time = int(utils.timestamp()) + seconds

    def mark_error(self, message):
        "标注一次错误执行"
        self.task.status = enums.Task.Status.Failure
        self.task.status_text = message
        self.task.executed = True
        self.message_append('danger', message)
        # 是否有必要继续执行的标记
        self.necessary = False

    def mark_success(self, message):
        "标注一次成功执行"
        self.task.status = enums.Task.Status.Success
        self.task.status_text = message
        self.task.executed = True
        self.message_append('success', message)

    @staticmethod
    def make_instance(task):
        "创建处理器实例"
        if task.type.value in _registered_handlers:
            return _registered_handlers[task.type.value](task)

        raise NotImplementedError(task.type.value)

class Task(storage):
    "任务实体"
    def __init__(self, **kwargs):
        super(Task, self).__init__(**kwargs)

        self.id = utils.intval(kwargs.get('id'))

        self.type = kwargs['type']
        if isinstance(self.type, (int, long)):
            self.type = enums.Task.Type.find(self.type)

        self.time_created = kwargs.get('time_created', int(utils.timestamp()))
        self.time_created_text = utils.timestamp2datefmt(self.time_created)
        self.active_time = kwargs.get('active_time', self.time_created)
        self.active_time_text = utils.timestamp2datefmt(self.active_time)
        self.last_time = kwargs.get('last_time', 0)

        self.tail_num = kwargs.get('tail_num', utils.make_tail_num(utils.randint(0, 999999999)))
        # 状态
        self.status = kwargs.get('status', enums.Task.Status.Waiting)
        if isinstance(self.status, (int, long)):
            self.status = enums.Task.Status.find(self.status)
        self.statsu_text = kwargs.get('status_text')

        self.exec_times = utils.intval(kwargs.get('exec_times', 0))

        self.content = kwargs.get('content', {})
        if self.content and isinstance(self.content, (str, unicode)):
            self.content = utils.json_loads(self.content)

        # 任务的处理程序，默认为None
        self._handler = None
        # 是否被执行过
        self._executed = False

    def save(self, mdb = None):
        "保存任务"
        if self.id > 0:
            TaskDAL.update(self, mdb = mdb)
        else:
            self.id = TaskDAL.add(self, mdb = mdb)

        return self

    def serialize2db(self, include_keys = None):
        "序列化任务实体为单层词典"
        result = {}
        for k, v in self.iteritems():
            if include_keys and k not in include_keys:
                continue

            if k in ('type', 'status'):
                v = v.value
            elif isinstance(v, (dict, storage, list, tuple,)):
                v = utils.json_dumps(v)

            result[k] = v

        return result

    def active(self):
        "激活当前任务实例所对应的任务记录"
        if self.id > 0 and self.status == enums.Task.Status.Failure:
            return TaskDAL.update_status(self.id, enums.Task.Status.Waiting.value, '')

        return False

    @staticmethod
    def create(type, tail_num = None, **kwargs):
        """
        创建任务
        :param type: 任务类型
        :param unique: 是否唯一任务
        :param kwargs:
        :return:
        """
        mdb = kwargs.pop('mdb', None)

        tail_num = tail_num or utils.make_tail_num(utils.randint(0, 999999999))

        task = Task(type = type, tail_num = tail_num)
        task.content.update(kwargs)
        task.save(mdb)
        return task

class TaskDAL(object):
    "任务相关的数据接口"
    @staticmethod
    def add_execlog(task, message, mdb = None):
        """
        添加任务执行日志
        :param task:
        :param message:
        :return:
        """
        if isinstance(message, (list, tuple, dict, storage)):
            message = utils.json_dumps(message)

        mdb = mdb or db.manager.master_core
        return mdb.insert('task_log', task_id = task.id
                          , status = task.status.value
                          , status_text = message
                          , status_time = web.SQLLiteral('UNIX_TIMESTAMP()'))

    @staticmethod
    def get_last_logs(task_id, limit):
        "获取给定条数给定任务的执行日志"
        rs = db.manager.slave_core.select('task_log'
                                          , where = 'task_id = $task_id'
                                          , order = 'id DESC'
                                          , limit = limit
                                          , vars = locals())
        return rs

    @staticmethod
    def update_status(task_id, status, status_text):
        "修改指定任务记录为指定状态"
        return db.manager.master_core.update('task'
                                             , status = status
                                             , status_text = status_text
                                             , where = 'id = $task_id'
                                             , vars = locals())

    @staticmethod
    def load(task_id):
        "获取给定任务记录"
        rs = db.manager.slave_core.select('task', where = 'id = $task_id', vars = locals())
        return Task(**rs[0]) if rs else None

    @staticmethod
    def update(task, mdb = None):
        "更新task记录"
        message = task.status_text
        if isinstance(message, (list, tuple, dict, storage)):
            message = utils.json_dumps(message)

        mdb = mdb or db.manager.master_core
        return mdb.update('task'
                          , last_time = web.SQLLiteral('UNIX_TIMESTAMP()')
                          , status = task.status.value
                          , status_text = message
                          , exec_times = web.SQLLiteral('exec_times + 1') if task.executed else web.SQLLiteral('exec_times')
                          , active_time = task.active_time
                          , where = 'id = $id'
                          , vars = task)

    @staticmethod
    def add(task, mdb = None):
        "添加任务记录"
        mdb = mdb or db.manager.master_core
        return mdb.insert('task'
                          , type = task.type.value
                          , content = utils.json_dumps(task.content)
                          , time_created = web.SQLLiteral('UNIX_TIMESTAMP()')
                          , active_time = task.active_time
                          , last_time = task.last_time
                          , tail_num = task.tail_num)

    @staticmethod
    def multi_add(task_values):
        "批量新增任务"
        assert(isinstance(task_values, list))

        include_keys = [
            'time_created','active_time','tail_num',
            'type', 'content',
        ]
        return db.manager.master_core.multiple_insert('task', [task.serialize2db(include_keys) for task in task_values])

    @staticmethod
    def find_actives(tail_nums = None, active_time = None, limit = 20):
        """
        获取达到指定激活时间的任务
        :param tail_nums: 尾号列表
        :param active_time:
        :param limit:
        :return:
        """
        # 默认激活时间为当前时刻
        active_time = active_time or int(utils.timestamp())
        # 附加查询条件
        attach_query = ''
        # 附加尾号
        if tail_nums:
            attach_query = ' AND tail_num IN (%s)' % ','.join([str(num) for num in tail_nums])

        # 默认获取状态为等待执行
        rs = db.manager.slave_core.query("""
            SELECT * FROM task WHERE status = 0 AND active_time <= $active_time%s ORDER BY active_time ASC, id ASC LIMIT $limit;
        """ % attach_query, vars = locals())
        return [Task(**r) for r in rs] if rs else None

    @staticmethod
    def find_status(status, limit = None):
        """
        获取指定状态的任务
        :param status:
        :return:
        """
        rs = db.manager.slave_core.select('task'
                                          , where = 'status = $status'
                                          , order = 'active_time DESC, id DESC'
                                          , limit = limit
                                          , vars = locals())
        return [Task(**r) for r in rs] if rs else None

    @staticmethod
    def query(status = None, offset = 0, limit = 20):
        """
        查询任务记录
        :param status:
        :param offset:
        :param limit:
        :return:
        """
        q = []
        if utils.greater_zero(status, True):
            q.append('status = $status')

        where = ''
        if q:
            where = 'WHERE %s' % ' AND '.join(q)

        sdb = db.manager.slave_core
        with sdb.transaction():
            rs = sdb.query("""
                SELECT SQL_CALC_FOUND_ROWS * FROM task %(where)s ORDER BY active_time DESC, id DESC LIMIT $offset, $limit;
            """ % locals(), vars = locals())
            if rs:
                rs2 = sdb.query("""SELECT FOUND_ROWS() AS total_records""")
                return storage(records = [Task(**r) for r in rs], total_records = rs2[0].total_records)

        return None