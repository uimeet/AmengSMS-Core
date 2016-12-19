# coding=utf-8

"""
授权管理
"""

from web.utils import storage
from collections import defaultdict

import db
from cache import cache, cache_delete
from core import utils

Config = storage(
    # 数据库相关配置
    DB = storage(
        # 授权表所载数据库名称
        Name = 'core',
        # 数据表
        Tables = storage(
            # 前缀
            Prefix = 'auth_',
            # 功能点表
            Function = 'function',
            # 角色表
            Role = 'role',
            # 角色与功能点关联表
            RoleFunctionMap = 'role_function',
            # 用户与角色关联表
            RoleMap = 'role_map',
        ),
    ),
)

class AuthRole(storage):
    "角色实体"
    def __init__(self, **kwargs):
        super(AuthRole, self).__init__(**kwargs)

        # 角色列表
        self._roles = storage()
        # 权限列表
        self._role_authcodes = []

    def _format_codes(self, codes):
        "格式化传入的权限码"
        if isinstance(codes, (str, unicode)):
            codes = codes.split(',')

        if not isinstance(codes, (list, tuple)):
            codes = [codes]

        return list(set(codes))

    def extend(self, dbrow):
        "将数据库记录合并到角色对象中"
        if dbrow.role_id not in self._roles:
            self._roles[dbrow.role_id] = {
                'id': dbrow.role_id,
                'name': dbrow.role_name,
                'auth_code': dbrow.role_auth_code,
                'functions': [],
            }

        self._roles[dbrow.role_id]['functions'].append({
            'id': dbrow.function_id,
            'name': dbrow.function_name,
            'type': dbrow.function_type,
            'code': dbrow.function_code,
        })

        # 添加到权限列表
        self._role_authcodes.append(dbrow.function_code)

    def filter(self, codes):
        "筛选出有效权限"
        codes = self._format_codes(codes)
        return filter(lambda x: x in self._role_authcodes, codes)

    def any(self, codes):
        codes = self._format_codes(codes)
        for code in codes:
            if code in self._role_authcodes:
                return True

        return False

    def all(self, codes):
        codes = self._format_codes(codes)
        return len(self.filter(codes)) == len(codes)

    def get_authcodes(self):
        "获取该授权角色所有授权码"
        return self._role_authcodes

    def get_role(self, role_id):
        "获取给定角色"
        return self._roles.get(role_id)

    def get_roles(self):
        "获取所有角色"
        return self._roles

class AuthDB(object):
    "授权管理的数据库接口对象"
    def __init__(self, config):
        self.config = config

    def _makedb(self, master = False):
        """
        执行给定sql
        @sql str 要执行的SQL
        @vars list sql语句中需要的参数
        @master bool 是否在master上执行
        """
        return db.manager['%s_%s' % ('master' if master else 'slave', self.config.Name)]

    def _maketable(self, table_name):
        return '%s%s' % (self.config.Tables.Prefix, table_name)

    def find_role_by_name(self, role_name):
        "获取给定登录名的角色"
        mdb = self._makedb()
        rs = mdb.select(self.role_table, where='name = $role_name', vars=locals())
        return rs[0] if rs else None

    @cache('Role-%(role_id)s')
    def find_role_by_id(self, role_id):
        "获取给定内码的角色"
        mdb = self._makedb()
        # 获取用户的所有权限
        rs = mdb.query("""
                    SELECT
                        r.id As role_id, r.name AS role_name, r.auth_code AS role_auth_code,
                        f.id AS function_id, f.name AS function_name, f.type AS function_type, f.code AS function_code
                    FROM
                        %(role)s AS r
                        INNER JOIN
                        %(role_function)s AS rf ON rf.role_id = r.id
                        INNER JOIN
                        %(function)s AS f ON f.id = rf.function_id
                    WHERE r.id = $role_id;
                """ % {
                'role': self._maketable(self.config.Tables.Role),
                'role_function': self._maketable(self.config.Tables.RoleFunctionMap),
                'function': self._maketable(self.config.Tables.Function),
            }, vars=locals())
        if rs:
            r = AuthRole()
            for row in rs:
                r.extend(row)

            return r.get_role(role_id)

        return None

    @cache_delete(['AllRoles', 'RoleFunction-%(role_id)s-True', 'RoleFunction-%(role_id)s-False', 'Role-%(role_id)s'])
    def update_role(self, role_id, role_name, function_ids):
        """
        更新角色
        """
        up = []
        # 是否有相同用户名的用户
        # 如果有则比较其id是否相同，如果相同，不更新用户名
        u = self.find_role_by_name(role_name)
        if u:
            if u.id != role_id:
                return 1
        else:
            up.append('name = $role_name')

        auth_code = ''
        # 生成授权签名
        function_ids = filter(lambda x: x > 0, [int(function_id) for function_id in function_ids])
        if function_ids:
            # 生成授权码
            auth_code = utils.md5( ','.join([str(fid) for fid in sorted(function_ids)]) )

        up.append('auth_code = $auth_code')

        mdb = self._makedb(True)
        with mdb.transaction():
            mdb.query('''UPDATE %s SET %s WHERE id = $role_id;''' % (self.role_table, ','.join(up)), vars=locals())
            # 删除原来的授权
            mdb.delete(self._maketable('role_function'), where = 'role_id = $role_id', vars = locals())
            if function_ids:
                # 更新授权
                values = []
                for fid in function_ids:
                    values.append({
                        'role_id': role_id,
                        'function_id': fid,
                    })
                mdb.multiple_insert(self._maketable('role_function'), values = values)

            return 0

        return 2

    @cache_delete('AllRoles')
    def add_role(self, role_name, function_ids):
        """
        添加角色
        @role_name str, 角色名
        """
        # 角色名是否存在
        if self.exists_role(role_name):
            return 1

        auth_code = ''
        # 生成授权签名
        function_ids = filter(lambda x: x > 0, [int(function_id) for function_id in function_ids])
        if function_ids:
            # 生成授权码
            auth_code = utils.md5( ','.join([str(fid) for fid in sorted(function_ids)]) )

        mdb = self._makedb(True)
        with mdb.transaction():
            aid = mdb.insert(self.role_table, name=role_name, auth_code=auth_code)
            if aid > 0:
                if function_ids:
                    # 更新授权
                    values = []
                    for fid in function_ids:
                        values.append({
                            'role_id': aid,
                            'function_id': fid,
                        })
                    mdb.multiple_insert(self._maketable('role_function'), values = values)
                return 0
        return 2

    def exists_role(self, role_name):
        "判定给定角色名是否存在"
        rs = db.manager.slave_core.query("""
                SELECT EXISTS(SELECT NULL FROM %s WHERE name = $role_name) AS ext;
                """ % self.role_table, vars=locals())
        return rs[0].ext

    @cache_delete('AllRoles')
    def delete_role(self, role_id):
        "删除给定角色名"
        mdb = self._makedb(True)
        with mdb.transaction():
            mdb.delete(self.rolefunc_table, where = 'role_id = $role_id', vars = locals())
            mdb.delete(self.rolemap_table, where = 'role_id = $role_id', vars = locals())
            return mdb.delete(self.role_table, where = 'id = $role_id', vars = locals())

    @cache('AllRoles')
    def find_roles(self):
        "获取所有角色"
        mdb = self._makedb()
        rs = mdb.select(self.role_table, order = 'id ASC')
        return list(rs)

    @cache('RoleFunction-%(role_id)s-%(todict)s')
    def find_functions_by_role(self, role_id, todict = False):
        "获取给定角色的授权"
        rs = self._makedb().query("""
            SELECT
              af.*
            FROM %(role_function)s AS arf
                INNER JOIN
                %(function)s AS af ON af.id = arf.function_id
            WHERE arf.role_id = $role_id;
        """ % {
            'role_function': self._maketable('role_function'),
            'function': self.func_table,
        }, vars = locals())
        if rs:
            if todict:
                return { f.id: f for f in rs }
            return rs
        elif todict:
            return {}

        return None

    @cache('all-functions')
    def find_all_functions(self):
        mdb = self._makedb()
        rs = mdb.select(self.func_table, order = 'type ASC, id ASC')
        if rs:
            result = defaultdict(list)
            for r in rs:
                result[r.type].append(r)

            return result
        return None

    @cache('UserRole-%(user_id)s', seconds = 60)
    def find_user_auths(self, user_id):
        "获取给定用户的所有角色及授权"
        mdb = self._makedb()
        # 获取用户的所有权限
        rs = mdb.query("""
            SELECT
                r.id As role_id, r.name AS role_name, r.auth_code AS role_auth_code,
                f.id AS function_id, f.name AS function_name, f.type AS function_type, f.code AS function_code
            FROM
                %(role_map)s AS rm
                INNER JOIN
                %(role)s AS r ON r.id = rm.role_id
                INNER JOIN
                %(role_function)s AS rf ON rf.role_id = r.id
                INNER JOIN
                %(function)s AS f ON f.id = rf.function_id
            WHERE rm.user_id = $user_id;
        """ % {
            'role_map': self._maketable(self.config.Tables.RoleMap),
            'role': self._maketable(self.config.Tables.Role),
            'role_function': self._maketable(self.config.Tables.RoleFunctionMap),
            'function': self._maketable(self.config.Tables.Function),
        }, vars = locals())
        if rs:
            r = AuthRole()
            for row in rs:
                r.extend(row)

            return r

        return None

    @property
    def role_table(self):
        "获取角色表"
        return self._maketable(self.config.Tables.Role)

    @property
    def func_table(self):
        "获取功能表"
        return self._maketable(self.config.Tables.Function)

    @property
    def rolemap_table(self):
        "获取role_map表"
        return self._maketable(self.config.Tables.RoleMap)

    @property
    def rolefunc_table(self):
        "获取role_function表"
        return self._maketable(self.config.Tables.RoleFunctionMap)


class Auth(object):
    "授权对象"
    def __init__(self, auth_user_id, config = Config):
        """
        实例化授权对象
        @auth_user_id int 认证用户内码
        @config storage 授权实例配置
        """
        self._db = AuthDB(config.DB)
        self.config = config
        self.user_id = auth_user_id
        self.role = self._db.find_user_auths(auth_user_id)

        assert (auth_user_id > 0)

    def __getattr__(self, item):
        attr = getattr(self._db, item, None)
        if attr:
            return attr

        attr = getattr(self.role, item, None)
        if attr:
            return attr

        raise AttributeError(item)

    def all(self, codes):
        "给定用户是否有给定所有权限"
        return self.role.all(codes) if codes else True

    def any(self, codes):
        "给定用户是否有给定权限中的任意一项权限"
        return self.role.any(codes) if codes else True

    def filter(self, codes):
        "筛选给定权限中 用户的有效权限"
        return self.role.filter(codes) if codes else True