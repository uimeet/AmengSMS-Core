# coding=utf-8

from web.utils import storage

from core.libs.enum import Enum


# 权限相关
Auth = storage(
    # 功能类型
    FunctionType = Enum(
        # 用户相关功能
        User = storage(value = 1, text = u'用户', tag = 'User'),
        # 管理用户相关功能
        Administrator = storage(value = 4, text = u'管理用户', tag = 'Administrator'),
        # 任务管理相关功能
        Task = storage(value = 99, text = u'任务管理', tag = 'Task'),
    ),
    # 角色的保存结果
    RoleSaveResult = Enum(
        # 成功
        Success = storage(value = 0, text = u'success', tag = 'Success'),
        # 角色名称重复
        NameDuplicated = storage(value = 1, text = u'角色名称重复', tag = 'NameDuplicated'),
        # 无操作
        NoOperation = storage(value = 2, texts = u'保存失败，无操作执行', tag = 'NoOperation'),

    ),
)

# 管理用户相关
Administrator = storage(
    # 状态
    Status = Enum(
        # 正常
        Normal = storage(value = 0, text = u'正常', tag = 'Normal', label = 'success'),
        # 登录锁定
        Locked = storage(value = 1, text = u'锁定', tag = 'Locked', label = 'danger'),
        # 删除
        Deleted = storage(value = 2, text = u'已删除', tag = 'Deleted', label = 'inverse'),
    ),
    SaveResult = Enum(
        # 成功
        Success=storage(value=0, text=u'success', tag='Success'),
        # 角色名称重复
        NameDuplicated=storage(value=1, text=u'角色名称重复', tag='NameDuplicated'),
        # 无操作
        NoOperation=storage(value=2, texts=u'保存失败，无操作执行', tag='NoOperation'),
    )
)

# 进程主机相关
SupervisorHost = storage(
    # 状态
    Status = Enum(
        Stopped = storage(value = 0, text = u'已停止', tag = 'Stopped'),
        Running = storage(value = 1, text = u'运行中', tag = 'Running'),
    ),
)

# 任务相关
Task = storage(
    # 类型
    Type = Enum(
        RechargeCheck = storage(value = 1, text = u'充值结果检查', tag = 'RechargeCheck'),
        WeixinSubscribe = storage(value = 2, text = u'微信公众号关注', tag = 'WeixinSubscribe'),
    ),
    # 状态
    Status = Enum(
        Waiting = storage(value = 0, text = u'等待执行', tag = 'Waiting', label = 'default'),
        Success = storage(value = 1, text = u'执行成功', tag = 'Success', label = 'success'),
        Failure = storage(value = 2, text = u'执行失败', tag = 'Failure', label = 'danger'),
    ),
)