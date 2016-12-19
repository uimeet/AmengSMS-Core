#!/usr/bin/env python
# encoding: utf-8
import settings

import web
from web.utils import storage

from core.libs import db, cache, auth, aes, ip
from core import utils

import enums


class Administrator(object):
    "管理员相关数据接口"

    @staticmethod
    def query(login_name = None, role_id = None, offset = 0, limit = 20):
        "查询管理用户"
        q = []
        if login_name:
            q.append("a.login_name LIKE '%s%%'" % login_name)
        if utils.greater_zero(role_id):
            q.append('r.id = $role_id')

        q = ('WHERE %s' % ' AND '.join(q)) if q else ''
        sdb = db.manager.slave_core
        with sdb.transaction():
            rs = sdb.query("""
                SELECT SQL_CALC_FOUND_ROWS
                    a.*,
                    GROUP_CONCAT(r.name) AS role_names
                FROM administrator AS a
                    INNER JOIN
                    auth_role_map AS arm ON arm.user_id = a.id
                    INNER JOIN
                    auth_role AS r ON r.id = arm.role_id
                %s
                GROUP BY a.id
                ORDER BY a.id DESC
                LIMIT $offset, $limit
            """ % q, vars = locals())
            if rs:
                records = []
                for r in rs:
                    del r.passwd
                    r.status = enums.Administrator.Status.find(r.status)
                    records.append(r)

                rs2 = sdb.query("""SELECT FOUND_ROWS() AS total_records;""")
                return storage(records = records, total_records = rs2[0].total_records)

        return None

    @staticmethod
    def find_scope(admin_id):
        "获取给定管理员管理范围"
        rs = db.manager.slave_core.select('administrator', what = 'scope', where = 'id = $id')
        return rs[0].scope if rs else None

    @staticmethod
    def make_invite_urls(user_id):
        "生成给定用户的邀请链接列表"
        hex_id = utils.id_to_hex(user_id)
        return ['http://%s/#/i/%s' % (domain, hex_id) for domain in settings.SITE_DOMAINS]

    @staticmethod
    def find_spread_settings(admin_id, todict = True):
        "获取给定管理员的推广设定"
        rs = db.manager.slave_lottery.query("""
            SELECT lottery_id, rebate FROM lottery_admin_rebate_spread_settings WHERE admin_id = $admin_id;
        """, vars = locals())
        if rs:
            if todict:
                return { r.lottery_id: r.rebate for r in rs }

            return rs
        elif todict:
            return {}

        return None

    @staticmethod
    def find_spread_settings_by_type(admin_id, todict=True):
        "获取给定管理员的推广设定"
        rs = db.manager.slave_core.query("""
                SELECT lottery_type, rebate FROM admin_rebate_spread_settings WHERE admin_id = $admin_id;
            """, vars=locals())
        if rs:
            if todict:
                return {r.lottery_type: r.rebate for r in rs}

            result = [0] * len(rs)
            for r in rs:
                result[r.lottery_type] = r.rebate

            return result
        elif todict:
            return {}

        return None

    @staticmethod
    def save_spread_settings(data):
        "保存管理员的推广设定"
        assert (isinstance(data, (list, tuple)))

        values = []
        for d in data:
            values.append('(%(admin_id)s, %(lottery_id)s, %(rebate)s)' % d)

        if values:
            return db.manager.master_lottery.query("""
                INSERT INTO lottery_admin_rebate_spread_settings(admin_id, lottery_id, rebate)
                VALUES%s
                ON DUPLICATE KEY UPDATE rebate = VALUES(rebate);
            """ % ','.join(values))

        return False

    @staticmethod
    def save_spread_settings_by_type(data):
        "保存管理员的推广设定"
        assert (isinstance(data, (list, tuple)))

        values = []
        for d in data:
            values.append('(%(admin_id)s, %(lottery_type)s, %(rebate)s)' % d)

        if values:
            return db.manager.master_core.query("""
                    INSERT INTO admin_rebate_spread_settings(admin_id, lottery_type, rebate)
                    VALUES%s
                    ON DUPLICATE KEY UPDATE rebate = VALUES(rebate);
                """ % ','.join(values))

        return False

    @staticmethod
    def find_by_name(login_name):
        "获取给定登录名的管理用户"
        rs = db.manager.slave_core.select('administrator'
                                          , where='login_name = $login_name', vars=locals())
        return rs[0] if rs else None

    @staticmethod
    def find_by_id(admin_id):
        "获取给定内码的管理用户"
        rs = db.manager.slave_core.select('administrator'
                                          , where='id = $admin_id', vars=locals())
        return rs[0] if rs else None

    @staticmethod
    def find_Administrator_role(admin_id=None,login_name=None):
        "获取管理员对应的角色信息"
        if admin_id:
            w = 'WHERE a.id = $admin_id'
        else:
            w = ''

        if login_name:
            n = 'WHERE a.login_name = $login_name'
        else:
            n = ''

        rs = db.manager.slave_core.query("""
            SELECT
                a.id,a.login_name,a.date_created,a.last_login,a.status,a.scope,
                r.id as rid,r.name
            FROM `administrator` AS a
                LEFT OUTER JOIN `auth_role_map` AS o ON o.user_id = a.id
                LEFT OUTER JOIN `auth_role` AS r ON r.id = o.role_id
            %(w)s
             %(n)s;
            """ % locals(), vars=locals())
        if admin_id or login_name:
            return rs[0] if rs else None
        else:
            return rs if rs else None

    @staticmethod
    def login_success(administrator_id):
        "给定用户登录成功后的操作"
        # 登录ip地址
        ipint = utils.real_ip_int()
        # 生成一个会话码
        session_code = utils.md5('%s%d%s' % (administrator_id, ipint, utils.timestamp()))
        # 获取地区
        loc = ip.location()

        mdb = db.manager.master_core
        with mdb.transaction():
            # 记录登录日志
            mdb.insert('administrator_logs'
                       , administrator_id = administrator_id, time_created = web.SQLLiteral('UNIX_TIMESTAMP()'), ip = ipint
                       , area = loc.get('area'), isp = loc.get('location'))
            if mdb.update('administrator'
                       , last_login = web.SQLLiteral('UNIX_TIMESTAMP()'), last_ip = ipint
                       , last_area = loc.get('area'), last_isp = loc.get('location')
                       , where = 'id = $administrator_id'
                       , vars = locals()):
                return session_code, loc

        return False, loc

    @staticmethod
    def exists(login_name):
        "判定给定管理员登录名是否存在"
        rs = db.manager.slave_core.query("""
                SELECT EXISTS(SELECT NULL FROM administrator WHERE login_name = $login_name) AS ext;
                """, vars=locals())
        return rs[0].ext

    @staticmethod
    def update(admin_id, login_name, passwd=None, role_ids=None, qq = None, mobile = None):
        """
        更新管理员
        @admin_id as str, 管理人员内码
        @login_name as str, 登录名
        @passwd as str, 密码
        @role as str, 角色
        @scope as list 管理范围
        """
        up = []
        # 是否有相同用户名的用户
        # 如果有则比较其id是否相同，如果相同，不更新用户名
        u = Administrator.find_by_name(login_name)
        if u:
            if u.id != admin_id:
                return enums.Administrator.SaveResult.NameDuplicated
        else:
            up.append('login_name = $login_name')

        # 是否修改密码
        if passwd:
            passwd = utils.md5(passwd)
            up.append('passwd = $passwd')

        if qq:
            up.append('qq = $qq')
        if mobile:
            up.append('mobile = $mobile')

        mdb = db.manager.master_core

        with mdb.transaction():
            # 修改管理员信息
            if up:
                mdb.query('''UPDATE administrator SET %s WHERE id = $admin_id;''' % ','.join(up), vars=locals())

            # 修改管理角色
            # 删除原来的角色关联
            mdb.delete('auth_role_map', where = 'user_id = $admin_id', vars = locals())
            # 更新新的管理角色关联
            if role_ids:
                values = []
                for role_id in role_ids:
                    values.append({
                        'user_id': admin_id,
                        'role_id': role_id,
                    })
                mdb.multiple_insert('auth_role_map', values)

            return enums.Administrator.SaveResult.Success

        return enums.Administrator.SaveResult.NoOperation

    @staticmethod
    def add(login_name, passwd, role_ids, qq = '', mobile = ''):
        """
        添加管理员
        @login_name as str, 登录名
        @passwd as str, 密码
        @role_ids as list, 角色id列表
        """
        # 用户名是否存在
        if Administrator.exists(login_name):
            return enums.Administrator.SaveResult.NameDuplicated

        mdb = db.manager.master_core
        with mdb.transaction():
            uid = mdb.insert('administrator'
                             , login_name=login_name
                             , passwd=utils.md5(passwd)
                             , status=enums.Administrator.Status.Normal.value
                             , date_created = web.SQLLiteral('NOW()')
                             , qq = qq
                             , mobile = mobile)
            if role_ids:
                values = []
                for role_id in role_ids:
                    values.append({
                        'user_id': uid,
                        'role_id': role_id,
                    })
                mdb.multiple_insert('auth_role_map', values)

            return enums.Administrator.SaveResult.Success

        return enums.Administrator.SaveResult.NoOperation

    @staticmethod
    def delete(admin_id):
        "删除给定管理员"
        return Administrator.set_status(admin_id, enums.Administrator.Status.Deleted.value)

    @staticmethod
    def lock(admin_id):
        "锁定给定管理员"
        return Administrator.set_status(admin_id, enums.Administrator.Status.Locked.value)

    @staticmethod
    def set_status(admin_id, status):
        "设置给定管理员的状态"
        return db.manager.master_core.update('administrator', status=status
                                             , where='id = $admin_id'
                                             , vars=locals())

    @staticmethod
    def find_all(login_name=None, todict = False):
        "获取所有管理员"
        q = ['status IN (1,0)']
        if login_name:
            q.append('login_name = $login_name')

        rs = db.manager.slave_core.query("""
            SELECT * FROM administrator WHERE %s;
            """ % ' AND '.join(q), vars=locals())
        if rs:
            if todict:
                return { r.id: r for r in rs }
            return rs
        elif todict:
            return {}

        return None

class AdministratorLog(object):
    "管理员日志"
    @staticmethod
    def add(type, administrator_id, content, mdb = None):
        """
        添加管理日志
        :param type: 操作类型
        :param administrator_id: 操作人内码
        :param content: 操作内容
        :return:
        """
        if isinstance(content, (web.utils.storage, dict)):
            content = utils.json_dumps(content)

        mdb = mdb or db.manager.master_core
        return mdb.insert('administrator_logs'
                                             , type = type.value
                                             , administrator_id = administrator_id
                                             , date_created = web.SQLLiteral('UNIX_TIMESTAMP()')
                                             , ip = utils.real_ip_int()
                                             , area = ''
                                             , location = ''
                                             , content = content)


def is_normal_session(session):

    "判断给定管理员账号会话状态是否为正常"
    if isinstance(session.id, (int, long)) and session.id > 0:
        a = Administrator.find_by_id(session.id)
        # 状态是否为1
        if a.status > 0:
            # 当前用户状态不为“正常”状态(为锁定用户)
            return 101
        if a.login_name != session.name:
            # 用户名不相同
            return 102
        # 验证成功
        return 0

    # 无效的会话
    return 103

def login(username, passwd, vcode, cookie = True, app = False, remember = False):
    """
    用户登录操作
    @username str 用户名
    @passwd str 密码，经过 md5(vcode + md5(passwd)) 混淆后的代码
    @vcode str 验证码
    @cookie bool 是否记录cookie
    @remember bool 是否长时间记录登录状态
    """
    if not username:
        return u'用户名不能为空'
    if not passwd:
        return u'密码不能为空'
    if not vcode:
        return u'验证码不能为空'

    u = Administrator.find_by_name(username)
    if not u:
        return u'用户不存在'
    # 检查用户状态
    if u.status == 1:
        return u'用户已被锁定，无法登录'
    elif u.status == 2:
        return u'用户已被删除'

    if passwd != utils.md5('%s%s' % (utils.md5(vcode.upper()), u.passwd)):
        return u'密码错误'

    # 登录成功
    session_code, loc = Administrator.login_success(u.id)
    if session_code:
        if cookie:
            # 记录登录状态
            AdminSession.save_state(u.id, u.login_name, session_code, remember)
        if app:
            # 记录APP状态
            AdminSession.save_appstate(u.id, u.login_name, session_code, remember)

        u.authorized_key = '%s%s%s' % (session_code[:16], u.id, session_code[16:],)
        u.location = loc
        u.hash_id = utils.id_to_hex(u.id)

        return u

    return u'登录失败，请稍候重试'


class AdminSession(object):
    '''
    表示一个管理用户登录会话
    '''
    # cookie名
    COOKIE_NAME = '__AVIUS__'

    def __init__(self, app = False):
        self.id = 0
        self.name = None
        self.app = app
        self.init()

    def init(self):
        '''
        执行初始化
        包括获取cookie原文并重新组织
        '''
        # 从cookie中获取的是密文
        # 此处需要解密
        sid = self._app_state() if self.app else self._web_state()

        # 解密失败或cookie中获取的None
        # 那么都认为是未登录
        if not sid:
            return

        vals = sid.split('$')
        # 值的格式不正确
        if len(vals) != 4:
            return

        self.id = utils.intval(vals[0])
        self.name = vals[1]
        # 昵称
        self.ip = utils.intval(vals[3])
        # 会话码
        self.session_code = vals[2]
        # 管理角色
        self.auth = auth.Auth(self.id)

    def _app_state(self):
        """
        App 端状态获取
        """
        key = web.ctx.env.get('HTTP_AUTHORIZED_KEY', None)
        if not key:
            key = utils.cookie('authorized_key')
        if not key:
            key = web.input().get('authorized_key', None)

        if key and len(key) > 32:
            # 会话码
            session_code = key[:16] + key[-16:]
            # 用户id
            uid = utils.intval(key[16:-16])
            if uid > 0:
                # 获取对应用户的服务端状态
                value = cache.manager.get('APP_ASC_%d' % uid)
                if value:
                    value = aes.decrypt(value, key_postfix = session_code[8:16])
                    return value

        return None

    def _web_state(self):
        "获取web会话状态"
        return utils.cookie(AdminSession.COOKIE_NAME)

    @property
    def authorized_key(self):
        """
        获取当前用户的授权key（仅APP模式有效）
        :return:
        """
        if not self.is_auth():
            return None

        value = cache.manager.get('APP_ASC_%d' % self.id)
        return ''.join([value[:16], str(self.id), value[-16:]])

    def is_auth(self):
        '''
        当前管理会话实例是否已通过验证
        '''
        return self.id > 0 and bool(self.name)

    def actived_session_code(self):
        "获取当前登录用户的 session_code"
        return cache.manager.get('ASC_%d' % self.id)

    def invite_links(self):
        "获取当前登录用户的邀请链接集合"
        return Administrator.make_invite_urls(self.id)

    def manage_scope(self):
        "获取后台管理范围"
        scope = Administrator.find_scope(self.id)
        scope = [int(s) for s in scope.split(',')] if scope else []

        if 0 in scope:
            return None
        elif self.id not in scope:
            scope.append(self.id)

        return scope


    @staticmethod
    def save_state(id, name, session_code, remmber = False):
        '''
        保存登录状态
        @id as int, 用户内码
        @name as string, 用户名称
        @session_code string, 会话码
        @remmber as bool, 是否记录状态，一周内
        '''
        if id <= 0 or not name:
            return False

        # 写入cookie
        utils.cookie(AdminSession.COOKIE_NAME, '%d$%s$%s$%d' % (id, name, session_code, utils.real_ip_int(length = 2)), minutes = 10080 if remmber else 120)
        # 缓存改session码
        cache.manager.set('ASC_%d' % id, session_code, seconds = 10080 * 60 if remmber else 120 * 60)
        return True

    @staticmethod
    def save_appstate(id, name, session_code, remmber = False):
        """
        保存登录状态（APP）
        """
        if id <= 0 or not name:
            return False

        value = '%d$%s$%s$%d' % (id, name, session_code, utils.real_ip_int(length = 2))

        cache.manager.set('APP_ASC_%d' % id
                          , aes.encrypt(value, key_postfix=session_code[8:16])
                          , seconds=10080 * 60 if remmber else 120 * 60)
        cache.manager.set('ASC_%d' % id, session_code)
        return True

    @staticmethod
    def logout():
        '''
        退出登录
        '''
        session = AdminSession.current(app=True)
        if not session.is_auth():
            return False

        cache.manager.delete('APP_ASC_%d' % session.id)
        utils.delcookie(AdminSession.COOKIE_NAME)

        return True

    @staticmethod
    def current(app = False):
        '''
        获取当前登录会话的管理员实例
        '''
        return AdminSession(app = app)
