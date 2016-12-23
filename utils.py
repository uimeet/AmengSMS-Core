# coding=utf-8

import re
import os
import binascii
import time
import urllib
import email
import random
import operator
import string
from datetime import datetime, timedelta
from collections import defaultdict, Iterable
import cStringIO
import base64
import decimal
import json
import hashlib
import itertools
import copy

import rsa
from pyDes import *
import qrcode
import markdown
import web
from web.utils import storage, re_compile
import inspect
import math

import settings

MD5_RE = re.compile(ur'[0-9A-Za-z]{32}', re.IGNORECASE)
def is_md5(src):
    "判断给定字符串是否是一个md5字符串"
    return bool(MD5_RE.match(src))

def fill_zero(num, minlength = 2):
    "当小于指定位数时，在数字前方补0"
    n = str(num)
    l = minlength - len(n)
    if l > 0:
        return '%s%s' % ('0' * l, num)

    return num

def call(func, default = None, **kwargs):
    return func(**kwargs) if callable(func) else default

def roll_equal(value, number = 100):
    "丢筛子并判断与给定值是否相等"
    return roll(number) == value

def roll(number = 100):
    """
    丢筛子
    @number as int, 可以丢出的最大值
    """
    return random.randint(1, max(number, 1))

def delete_file(path):
    "删除文件"
    if path and os.path.isfile(path):
        os.remove(path)

def delete_dirs(path):
    "递归删除给定路径"
    import shutil
    if path and os.path.isdir(path):
        shutil.rmtree(path)

def make_dirs(path):
    "创建不存在的目录"
    if path and not os.path.isdir(path):
        os.makedirs(path)

SIZE_UNITS = ('Bytes', 'KB', 'MB', 'GB', 'TB', 'PB',)
def size2human(size):
    "将文件字节大小转换为最接近的大单位"
    i = 0

    while size > 1024:
        i += 1
        size /= 1024.

    return '%s %s' % (round(size, 2), SIZE_UNITS[i])

def extension(path):
    "获取给定路径下文件的扩展名"
    return os.path.splitext(path)[1]

def is_http():
    "判断当前会话是否是http会话"
    return web.ctx and 'env' in web.ctx

def parse_trade_id(trade_id):
    """
    将给第三方api平台使用的交易id转换为本平台交易id
    :param trade_id:
    :return:
    """
    return intval(trade_id.replace(settings.SITE_PREFIX, ''))

def make_trade_id(transaction_id):
    """
    生成给定交易记录的第三方接口交易id
    :param transaction_id:
    :return:
    """
    return '%s%s' % (settings.SITE_PREFIX, transaction_id)

def list2entity(rs, entity_cls):
    """
    将一个列表转换为给定实体类的列表
    :param rs: 要转换为列表，里面每个元素只能是dict的子类
    :param entity_cls: 实体类
    :return:
    """
    if rs:
        return [entity_cls(**r) for r in rs]

    return None

DOMAIN_RE = re.compile('^(?=^.{3,255}$)[*a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+$', re.IGNORECASE)
def is_domain(src):
    "判断给定文本是否是有效的域名格式"
    return bool(DOMAIN_RE.match(src))

def floor(num):
    "对给定数字向下取整"
    return math.floor(num)

def ceil(num):
    "对给定数字向上取整"
    return math.ceil(num)

def split_item(src, index, sep = ',', format = None):
    vals = src.split(sep)
    if index >= len(vals):
        return None

    return format(vals[index]) if callable(format) else vals[index]

def clone(obj):
    return copy.copy(obj)

def any_equals(keyvalues, value, keys = None):
    """
    判断给定词典中,是否有任意一个key的值等于给定值value
    :param keyvalues: 键值对
    :param value: 要判定的值
    :return:
    """
    for k, v in keyvalues.iteritems():
        if keys:
            if k in keys and v == value:
                return True
        elif v == value:
            return True

    return False

def is_iterable(src):
    """
    判断给定对象是否是一个可枚举对象
    :param src:
    :return:
    """
    return isinstance(src, Iterable)

def make_tail_num(seed = None):
    """
    生成时间戳
    :param seed: 种子值, 默认为当前时间戳
    :return:
    """
    seed = seed or int(timestamp())
    return seed % 251

MD5_RE = re.compile(ur'^[0-9A-Fa-f]{32}$', re.IGNORECASE)
def is_md5(src):
    """
    判定给定字符串是否是一个MD5字符串
    :param src:
    :return:
    """
    if src:
        return MD5_RE.match(src)

    return False

def is_date(src):
    """
    判断给定变量是否是一个datetime实例
    :param src:
    :return:
    """
    return isinstance(src, datetime)

def code_filter(codes, vvs = None, func = None):
    """
    投注号码过滤
    :param codes:
    :param vvs:
    :return:
    """
    if codes:
        return num_filter(list(set([func(code) if callable(func) else code for code in codes.split('&')])), vvs)

    return codes

def num_filter(nums, vvs = None):
    """
    过滤给定数字集合, 找出所有在给定范围内的数字
    :param nums: 要过滤的数字集合
    :param vvs: 有效的值范围
    :return:
    """
    if nums:
        # 默认的数字有效范围 0-9
        vvs = vvs or range(10)
        return list([num for num in nums if intval(num, -1) in vvs])

    return nums

def list2set(lst):
    """
    过滤列表元素
    :param lst:
    :return:
    """
    return [v for v, k in itertools.groupby(sorted([sorted(cod) for cod in lst]))]

def list2product(lst, baozi = False):
    """
    将列表对乘展开
    :param lst:
    :return:
    """
    if lst and len(lst) > 1:
        lst2 = list(itertools.product(*[lst] * len(lst)))
        # 过滤重复组合
        lst2 = [v for v, k in itertools.groupby(sorted(lst2))]
        if not baozi:
            lst2 = [nums for nums in lst2 if len(set(nums)) >= 2]

        return lst2

    return None


def list2str(lst, sep = ','):
    """
    将给定列表转为字符串
    :param lst: 列表
    :param sep: 间隔符
    :return:
    """
    if lst:
        return sep.join([str(l) for l in lst])

    return None

def check_params(names, params):
    """
    检查给定参数集,是否包含所有指定名称的参数
    :param names: list 要检查的参数名列表
    :param params: 待检查参数集合
    :return:
    """
    if not all(k in params for k in names):
        return False

    return True

def make_checksum(salt, values):
    """
    生成给定值的校验和
    :param salt: salt 值
    :param values: 要生成校验码的值
    :return: char(32)
    """
    if isinstance(values, tuple):
        values = list(values)
    if not isinstance(values, list):
        values = [values]

    values.append(salt)
    return md5(':'.join([str(v) for v in values]))


def hex2tuple(src, sep = ':'):
    "将一个16进制字符串转换为元组"
    assert(src)

    src = hex_des(src)
    if src:
        values = src.split(sep)
        return tuple(values)

    return None

def tuple2hex(src, sep = ':'):
    "将一个元组转换成16进制数据"
    assert(isinstance(src, (tuple, list)))
    return des_hex(sep.join([str(s) for s in src]))

def merge_dict(lhs, rhs, keys = None):
    """
    合并两个词典中的key
    :param lhs: 合并的目标词典
    :param rhs: 被合并词典
    :param keys: 要可以并的key是列表,如果不提供,默认为 rhs 的所有key
    :return: 返回合并后的词典
    """
    if keys and isinstance(keys, (list, tuple)):
        for key in keys:
            if rhs.has_key(key):
                lhs[key] = rhs[key]
    else:
        lhs.update(rhs)

    return lhs

def is_method(func):
    "判断给定函数是否是一个类方法"
    return inspect.ismethod(func)

def is_function(func):
    "判断给定函数是否一个函数"
    return inspect.isfunction(func)

def arrange_args(func, *kargs, **kwargs):
    "整理并返回给定函数的参数及值"
    args = {}

    argNames = inspect.getargspec(func)
    if argNames:
        # 初始化参数列表
        args = { arg: '' for arg in argNames.args }
        # 填充默认值
        if argNames.defaults:
            for idx, value in enumerate(argNames.defaults[::-1]):
                args[argNames.args[len(args) - idx - 1]] = value

        if kargs:
            for idx, value in enumerate(kargs):
                args[argNames.args[idx]] = value
        if kwargs:
            args.update(kwargs)

    return args

def next(iterator, default = None):
    "对内建next方法的封装"
    try:
        return next(iterator)
    except StopIteration, e:
        return default

def calc_odds(max_tickets, bouns_rate, price):
    """
    计算彩种的赔率
    @max_tickets int 彩种最大可购注数
    @bouns_rate float 奖金比例
    @price int 单价
    """
    return str(int(max_tickets * bouns_rate * price))[:4]

def dict2url(d, exclude = []):
    "将词典转换为url"
    query = urllib.urlencode({k: v.encode('utf-8') if isinstance(v, unicode) else v for k, v in d.iteritems() if k not in exclude})
    return query

def dbset2dict(dbset, keyfmt):
    "将数据库结果集转换为词典"
    result = {}
    for ds in dbset:
        result[keyfmt % ds] = ds

    return result

def filedir(fn):
    return '/'.join(fn.split('/')[:-1])

def printf(text):
    "打印日志到控制台"
    try:
        print '[%s] - %s' % (now(), text, )
    except:
        print '[%s] - %s' % (now(), text.encode('utf-8'), )

def dict_clear(d):
    "清空词典中的所有值"
    if d:
        for k in d.keys():
            d[k] = ''
        return d

    return None

htmlCodes = [
    ['&', '&amp;'],
    ['<', '&lt;'],
    ['>', '&gt;'],
    ['"', '&quot;'],
]
htmlCodesReversed = htmlCodes[:]
htmlCodesReversed.reverse()
def html_decode(s, codes=htmlCodesReversed):
    """ 解码htmlEncode后的代码"""
    for code in codes:
        s = s.replace(code[1], code[0])
    return s

def html_encode(s, codes=htmlCodes):
    """ 编码html标签"""
    for code in codes:
        s = s.replace(code[0], code[1])
    return s

def url(encode = False):
    "获取当前访问地址的完整路径"
    url = '%s://%s%s' % (web.ctx.protocol, web.ctx.host, web.ctx.fullpath)
    if encode:
        return urlencode(url)

    return url

def mobile_visit():
    "判断是否来自手机端访问"
    userAgent = web.ctx.env.get('HTTP_USER_AGENT', '')

    _long_matches = r'googlebot-mobile|android|avantgo|blackberry|blazer|elaine|hiptop|ip(hone|od)|kindle|midp|mmp|mobile|o2|opera mini|palm( os)?|pda|plucker|pocket|psp|smartphone|symbian|treo|up\.(browser|link)|vodafone|wap|windows ce; (iemobile|ppc)|xiino|maemo|fennec'
    _long_matches = re.compile(_long_matches, re.IGNORECASE)
    _short_matches = r'1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|e\-|e\/|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|xda(\-|2|g)|yas\-|your|zeto|zte\-'
    _short_matches = re.compile(_short_matches, re.IGNORECASE)

    if _long_matches.search(userAgent) != None:
        return True

    user_agent = userAgent[0:4]
    if _short_matches.search(user_agent) != None:
        return True

    return False

def list_find(lst, fn):
    for l in lst:
        if fn(l):
            return l
    return None

def p(text):
    text = text.replace('\n', '<br />')
    return text

def md(text):
    return markdown.markdown(text)

def make_qrcode(text, version = 1):
    "生成给定内容成二维码的base64编码"
    img = qrcode.make(text)
    sio = cStringIO.StringIO()
    img.save(sio, kind = 'PNG')
    return base64.b64encode(sio.getvalue())

LABELS = ('default', 'primary', 'success', 'info', 'warning', 'danger', 'inverse', 'green', 'purple', 'pink',)
def rand_label(basenum = None):
    if basenum:
        return LABELS[basenum % len(LABELS)]
    return random.choice(LABELS)

def safe_excel(text):
    "安全的excel字符串"
    text = text.replace(u"'", u"‘")
    text = text.replace(u"`", u"’")
    return text

def seplen(src, separator = ','):
    "统计一个字符串按给定间隔符分割后的长度"
    return len(src.split(separator)) if src else 0

def if_echo(expr, true, false = ''):
    "条件输出文本"
    return true if expr else false

def money2cent(src):
    "讲一个“元”为单位的金额转换为“分”为单位的金额"
    if isinstance(src, (int, long)) and src == 0:
        return '0'
    if not isinstance(src, (str, unicode)):
        src = str(src)

    src = src.split('.')
    if len(src) == 1:
        src.append('00')
    elif len(src) == 2:
        if len(src[1]) == 1:
            src[1] += '0'
    return ''.join(src)

def cent2money(src):
    "将一个“分”为单位的金额转换为“元”"
    if src:
        src = str(src)
        lhs, rhs = src[:-2], src[-2:]
        if rhs and rhs != '00':
            return '%(lhs)s.%(rhs)s' % locals()

        return lhs
    return str(src)

HTML_RE = re.compile(ur'<[^>]+>')
def clean_html(src):
    "清除所有html标签"
    return HTML_RE.sub('', src).strip() if src else ''

def str2date(src, fmt = '%Y-%m-%d'):
    "将字符串日期转换为datetime对象"
    if src:
        try:
            return datetime.strptime(src, fmt)
        except:
            return None
    return src

def int2date(src, fmt = '%Y-%m-%d'):
    "将整型日期转换为给定格式"
    src = str(src)
    if len(src) != 8:
        return src

    date = datetime(int(src[:4]), int(src[4:6]), int(src[6:]))
    if fmt:
        return date.strftime(fmt)

    return date

def date2int(src, fmt = '%Y-%m-%d'):
    "将传入的日期转换为整型"
    if src:
        try:
            d = datetime.strptime(src, fmt)
            return intval(d.strftime('%Y%m%d'))
        except ValueError as ve:
            return 0
    return 0

def dbset_sum(raw, keys = None, ekeys = None):
    """
    将一个数据库集合各个字段求和
    @raw as list, 原始数据集
    @keys as list, 需要求和的字段列表
                当@keys为None时，对所有字段各自求和
    @ekeys as list, 要排除的字段列表
    """
    assert(raw)
    assert(isinstance(raw, list))

    if not isinstance(keys, (tuple, list,)):
        keys = raw[0].keys()
    if ekeys and isinstance(ekeys, (tuple, list,)):
        keys = filter(lambda x: x not in ekeys, keys)

    result = defaultdict(int)
    for r in raw:
        for key in keys:
            result[key] += r.get(key, 0)
    return result

def dict_sum(dic, keys, attr_names, default = 0, method = operator.attrgetter):
    """
    安全获取并累加一个词典对象中多个成员的多个给定属性
    @dic as dict, 词典对象实例
    @keys as list, 词典key的列表
    @attr_names as list, 属性名列表
    @default as int, 当给定属性不存在时，给定的默认值
    @method as func, 获取属性使用的方法，默认为attrgetter
    """
    if not dic:
        return default
    if not isinstance(keys, (list, tuple)):
        keys = [keys]
    if not isinstance(attr_names, (list, tuple)):
        attr_names = [attr_names]

    retval = 0
    for key in keys:
        if key in dic:
            for attr_name in attr_names:
                try:
                    retval += int(method(attr_name)(dic[key]))
                except:
                    retval += default
        else:
            retval += default

    return retval

def dict_get(dic, key, attr_name, default = None, method = operator.attrgetter):
    """
    安全获取一个词典对象中成员的属性
    @dic as dict, 词典对象实例
    @key as str/int/..., 成员的key
    @attr_name as str, 要获取词典对象成员的属性名称
    @default as %, 默认值，当获取的key或attr_name不存在时返回
    @method as func, 使用的方法，默认为attrgetter
    """
    if dic and key in dic:
        try:
            return method(attr_name)(dic[key])
        except:
            pass

    return default

def time_add(bd, seconds):
    "在给定时间上添加给定的秒数"
    td = timedelta(seconds = seconds)
    return bd + td

def value2key(data, key, value, sort = True):
    "将给定列表中的value字段转换为key，相同的value进行合并"
    assert(isinstance(data, (list, tuple)))

    retval = defaultdict(list)
    for d in data:
        retval[d[value]].append(d[key])

    retval = [{'name': v, 'value': k} for k, v in retval.iteritems()]
    if sort:
        return sorted(retval, key = operator.itemgetter('value'), reverse = True)

    return retval

def echarts_loc(loc):
    "将给定省市地点名转换为echarts所需的格式"
    postfix = [
            u'省', u'市', u'自治区', u'特别行政区',
            u'维吾尔族', u'壮族', u'回族']
    for p in postfix:
        loc = loc.replace(p, '')
    return loc

def convert_echarts_map(data, loc_field, value_field = 'total_records', sort = True):
    """
    将给定数据转换为ECharts Map报表所需格式数据
    @data as list, 数据列表
    @loc_field as str, 地点字段名
    @value_field as str, 值字段名
    """
    if not isinstance(data, list):
        data = list(data)
    data = [{'name': echarts_loc(d[loc_field]), 'value': d[value_field]} for d in data]
    if sort:
        data = sorted(data, key = operator.itemgetter('value'), reverse = True)

    return {
            #'min': min(data, key = operator.itemgetter('value')),
            'max': max(data, key = operator.itemgetter('value')),
            'data': data,
        }

def sign_rate(sign_orders, declined_orders):
    "计算签收/拒签率"
    if sign_orders > 0:
        return round(sign_orders * 1. / (sign_orders + declined_orders) * 100, 2)

    return 0

def greater_zero(num, equal = False):
    "判断给定数字是否大于0"
    if isinstance(num, (int, long, float, decimal.Decimal)):
        return num >= 0 if equal else num > 0

    return False

def int2us(num):
    "将数字按欧美显示法显示"
    n = str(num)

    r = []
    for i in xrange(len(n)):
        if (i + 1) % 3 == 0:
            r.append(',')
        r.append(n[i])
    return ''.join(r)

def int2human(num):
    "将数字转换为人类可识别的文字"
    num = int(num)
    if num < 10000:
        return '%s元' % num
    return '%s万' % round(num / 10000., 3)

def year():
    "获取当前年份"
    return now('%Y')

def delsession(name):
    if 'session' in web.ctx:
        del web.ctx.session[name]
    else:
        delcookie(name)

def session(name, value = None):
    if 'session' in web.ctx:
        if value:
            web.ctx.session[name] = value
            return value
        else:
            return web.ctx.session.get(name, None)
    else:
        return cookie(name, value)

def delcookie(name, path = '/', domain = None):
    "删除给定cookie"
    web.setcookie(name, None, path = path, domain = domain ,expires = -1)

def cookie(name, value = None, minutes = 60 * 24, path = '/', domain = None, encode = True):
    """
    获取或写入cookie
    @name as str, cookie名称
    @value as str, cookie值，如果不提供表示读取
    @minutes as number, cookie有效的分钟数，可以是小数
    @path as str, cookie有效的路径
    @domain as str, cookie有效的域名
    @encode as bool, cookie是否加密
    """
    if value is None:
        value = web.cookies().get(name, None)
        if value:
            if encode:
                return hex_des(value)
            else:
                return value
        return value
    else:
        web.setcookie(name, des_hex(value) if encode else value, expires = minutes * 60, domain = domain, path = path)
        return value

HEX_RE = re.compile(r'[0-9A-F]', re.IGNORECASE)
def is_hex(src):
    "判定给定字符串是否是一个16进制字符串"
    if src:
        return HEX_RE.match(src)

    return False

def enum2des(src):
    "将一个可枚举的对象进行des加密"
    if src:
        assert(enumerate(src))
        return des_hex(json_dumps(src))

    return None

def des2enum(src):
    "将一个枚举对象的加密密文进行des解密"
    if src:
        return json_loads(hex_des(src))

    return None

def safe_qq(qq):
    "显示安全的qq"
    if qq:
        l = len(qq)
        w = 2
        if l <= 5:
            w = 1

        return '%s%s%s' % (qq[:w], '*' * (l - (w * 2)), qq[-w:])

    return ''

def safe_name(name):
    "显示安全的名称，只显示姓名的最后一个字"
    if name:
        if not isinstance(name, unicode):
            name = unicode(name, 'utf-8')

        l = len(name)
        return '%s%s' % ('*' * (l - 1), name[-1])
    return ''

def safe_mobile(src):
    "显示安全的手机号，只显示前三位和后三位"
    if src:
        return '%s%s%s' % (src[:3], '*' * 5, src[-3:])

    return ''

def safe_email(src):
    "显示安全的邮箱地址"
    if src:
        values = src.split('@')
        return '%s%s%s@%s' % (values[0][0], '*' * len(values[0][1:-1]), values[0][-1], values[1])

    return ''

def cmp_csrf_input():
    "比较csrf隐藏域的值是否有效"
    return cmp_csrf_token(web.input().get('CSRF', None))

def make_csrf_input():
    "创建一个csrf隐藏域"
    return '<input type="hidden" name="CSRF" value="%s" />' % make_csrf_token()

def cmp_csrf_token(text):
    "比较传入的 TOKEN 是否一致"
    token = session('__CSRF__')
    if token:
        delsession('__CSRF__')
        return cmp(text, token) == 0

    return False

def make_csrf_token():
    "生成一个 TOKEN"
    import uuid
    # 生成一个随机字符串作为token
    token = str(uuid.uuid1())
    # 存入session
    return session('__CSRF__', token)

MOBILE_RE = re.compile(ur'^1[0-9]{10}$')
def is_mobile(src):
    "判定是否是手机号"
    if is_empty(src):
        return False
    if len(src) != 11:
        return False
    return MOBILE_RE.match(src)

def is_empty(src):
    "判定给定值是否为空"
    return src is None or src.strip() == ''

def des_hex(src):
    "使用 des 加密后，转换为16进制返回"
    try:
        return binascii.b2a_hex(encrypt(src))
    except:
        return None

def hex_des(src):
    "将16进制字符串进行des解密后返回"
    if src:
        try:
            return decrypt(binascii.a2b_hex(src))
        except:
            return None
    return src

def date_valid(lts, seconds, rts = None):
    """
    给定日期对象是否有效
    """
    assert(isinstance(lts, datetime))
    rts = rts or datetime.now()
    return time_valid(int(lts.strftime('%s')), seconds, int(rts.strftime('%s')))

def time_valid(lts, seconds, rts = None):
    """
    时间是否有效，给定时间戳是否在给定的秒数内
    @lts as int, 要验证的时间戳
    @rts as int, 参照时间戳，默认当前时间
    @seconds as int, 要验证的秒数
    """
    # 不提供rts参数则为当前时间
    rts = rts or time.time()
    # 计算时间增量
    td = datetime.fromtimestamp(rts) - datetime.fromtimestamp(lts)
    return (td.days * 86400 + td.seconds) < seconds

def timestamp2datefmt(ts, fmt = '%Y-%m-%d %H:%M:%S'):
    "时间戳转换为date的字符串格式"
    return timestamp2date(ts).strftime(fmt)

def timestamp2date(ts, fmt = None):
    "时间戳转换为date类型"
    d = datetime.fromtimestamp(ts)
    return d.strftime(fmt) if fmt else d
web.template.Template.globals['ts2date'] = timestamp2date

def timestamp():
    "获取当前时间戳"
    return time.time()

def sort(l, key = None, reverse = False):
    "排序列表"
    assert(isinstance(l, (list, tuple)))

    if key:
        key = operator.itemgetter(key)
    return sorted(l, key = key, reverse = reverse)

def get_referer():
    """
    获取 HTTP_REFERER
    """
    return web.ctx.env.get('HTTP_REFERER', None)

def url2domain(url, title = True):
    "提取url中的域名信息"
    from urlparse import urlparse
    assert(isinstance(url, (str, unicode)))

    up = urlparse(url)
    if title:
        return up.netloc.lower().capitalize()
    else:
        return up.netloc.lower()

def if_empty(src, default):
    "如果给定 @src 为 None或空字符串，将返回 @default"
    return src if src else default

def sleep(seconds):
    "休眠指定时间"
    time.sleep(seconds)

def rand_sleep(l = 3, u = 5):
    "随机休眠"
    delay = random.randint(l, u)
    time.sleep(delay)

# 与中文匹配的正则表达式
CHINESE_RE = re.compile(u'[\u2E80-\u9fFF]+')
def is_chinese(text):
    """根定文字中是否包含中文"""
    if text:
        # 如果传入对象不是 unicode
        if not isinstance(text, unicode):
            try:
                text = unicode(text, 'utf-8')
            except UnicodeDecodeError, e:
                print e
        # 进行一次查找
        return bool(CHINESE_RE.search(text))
    return False

def input(name, default = None):
    return web.input().get(name, default)

def input_query(name, flag = True):
    val = input(name)
    if val:
        return '%s%s=%s' % ('&' if flag else '', name, val,)
    return ''

def sql_escape(text):
    "转移sql的非法字符"
    if not isinstance(text, (str, unicode,)):
        return text

    return text \
            .replace("\\", r"\\") \
            .replace("'", r"\'") \
            .replace("$", "$$") \
            .replace("%", "\%")

def sql_unescape(text):
    "反转sql的非法字符"
    return text \
            .replace("\%", "%") \
            .replace("$$", "$") \
            .replace(r"\'", "'") \
            .replace(r"\\", "\\")

def sample(lst, num):
    """
    从指定列表中随机抽样给定条数的记录
    :param lst:
    :param num:
    :return:
    """
    retval = random.sample(lst, num)
    if retval:
        if num == 1:
            return retval[0]
    return retval

def random_str(length = 10):
    "生成一个随机字符串"
    return ''.join(random.sample(string.letters + string.digits, length))

def random_digits(length = 10):
    "生成一个随机字符串"
    return ''.join(random.sample(string.digits, length))

def str2timestamp(src, fmt = '%Y-%m-%d', format = None):
    "将给定日期字符串转换为时间戳"
    ta = time.strptime(src, fmt)
    ts = time.mktime(ta)
    return format(ts) if callable(format) else ts

def minutes_delta(minutes, basedate = None, fmt = None):
    """
    获取给定加减分钟的日期
    :param minutes: 加减的分钟数
    :param basedate: 基于的时间
    :param fmt: 格式化格式
    :return:
    """
    basedate = basedate or datetime.now()
    if fmt:
        return (basedate + timedelta(minutes=minutes)).strftime(fmt)

    return basedate + timedelta(minutes=minutes)

def hours_delta(hours, basedate = None, fmt = None):
    """
    获取给定加减小时后的日期
    @hours as int 加减小时
    @basedate as datetime, 基于的时间，默认为now
    @fmt as str, 一个格式化模板，如果提供该参数，方法将返回str类型，不提供返回datetime类型
    """
    basedate = basedate or datetime.now()
    if fmt:
        return (basedate + timedelta(hours = hours)).strftime(fmt)

    return basedate + timedelta(hours = hours)

def days_delta(days, basedate = None, fmt = None):
    """
    获取给定加减天数后的日期
    @days as int, 加减天数
    @basedate as datetime, 基于的时间，默认为now
    @fmt as str, 一个格式化模板，如果提供该参数，方法将返回str类型，不提供返回datetime类型
    """
    basedate = basedate or datetime.now()
    if fmt:
        return (basedate + timedelta(days = days)).strftime(fmt)

    return basedate + timedelta(days = days)

def seven_days_bound():
    "获取７天的时间范围值"
    return days_bound(7)

def days_bound(days):
    "获取给定天数之前的日期到今天的日期期间"
    u = datetime.now()
    # 获取７天后的时间
    l = u - timedelta(days = days)

    return int(l.strftime('%Y%m%d')), int(u.strftime('%Y%m%d'))

def month_bound():
    "获取当月的日期范围整数值"
    m = month_index()
    return int('%d01' % m), int('%d%d' % (m, 28 if m == int('%s02' % year()) else 30))

def month_index():
    "获取当月的日期整数值"
    return int(datetime.now().strftime('%Y%m'))

def now(fmt = None):
    "获取当前日期"
    return datetime.now().strftime(fmt) if fmt else datetime.now()

def deltadate(**kwargs):
    return timedelta(**kwargs)

def yesterday_index():
    "获取昨天的日期整数值"
    return int((datetime.now() - timedelta(days = 1)).strftime('%Y%m%d'))

def yesterday(fmt = '%Y-%m-%d'):
    return days_delta(-1, fmt = fmt)

def today(fmt = '%Y-%m-%d'):
    return datetime.now().strftime(fmt)

def today_index():
    "获取当日的日期整数值"
    return int(datetime.now().strftime('%Y%m%d'))

def today_timestamp():
    "获取当日时间戳区间"
    today = datetime.now().strftime('%Y-%m-%d')
    star_time = int(time.mktime(time.strptime(today + ' 00:00:00', '%Y-%m-%d %H:%M:%S')))
    return star_time

def today_timestamp_range():
    "获取当日时间戳区间"
    today = datetime.now().strftime('%Y-%m-%d')
    star_time = int(time.mktime(time.strptime(today + ' 00:00:00', '%Y-%m-%d %H:%M:%S')))
    end_time = star_time + 86399
    return [star_time, end_time]

def str2hash(src, length = 8):
    """
    计算一个字符串的哈希值
    @src as str, 要转换的字符串
    @length as int, 位数
    """
    return int(hashlib.sha1(src).hexdigest(), 16) % (10 ** length)

def json_loads(src):
    if src is not None:
        try:
            return json.loads(src)
        except ValueError as e:
            print e

    return None

class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (tuple, list)):
            return [self.encode_object(x) for x in obj]
        else:
            return self.encode_object(obj)

    def encode_object(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return str(obj)
        if isinstance(obj, (dict, storage)):
            return { k: v for k, v in obj.iteritems() if k[0] != '_' }
        if isinstance(obj, Input):
            return None

        return obj

def json_dumps(obj, encoder = None):
    if obj is not None:
        try:
            return json.dumps(obj, cls = encoder)
        except ValueError as e:
            print e

    return None

def ip2int(ip):
    import struct, socket
    return struct.unpack("!I",socket.inet_aton(ip))[0]

def int2ip(i):
    import struct, socket
    return socket.inet_ntoa(struct.pack("!I",i))

def real_ip_int(env = None, length = 4):
    return ip2int(real_ip(env, length = length))

def real_ip(env = None, length = 4):
    "获取环境变量中的真实IP"
    if web.ctx:
        env = web.ctx.env

    ip = None
    if env:
        if 'HTTP_ALI_CDN_REAL_IP' in env:
            ips = env['HTTP_ALI_CDN_REAL_IP'].split(',')
            ip = ips[0].strip()
        if not ip and 'HTTP_REMOTEIP' in env:
            ips = env['HTTP_REMOTEIP'].split(',')
            ip = ips[0].strip()
            #print 'HTTP_REMOTEIP', env['HTTP_REMOTEIP']
        if not ip and 'HTTP_X_FORWARDED_FOR' in env:
            ips = env['HTTP_X_FORWARDED_FOR'].split(',')
            ip = ips[0].strip()
            #print 'HTTP_X_FORWARDED_FOR', env['HTTP_X_FORWARDED_FOR']
        if ip is None and 'HTTP_CLIENT_IP' in env:
            #print 'HTTP_CLIENT_IP', env['HTTP_CLIENT_IP']
            return env['HTTP_CLIENT_IP']
        if ip is None and 'REMOTE_ADDR' in env:
            #print 'REMOTE_ADDR', env['REMOTE_ADDR']
            ip = env['REMOTE_ADDR']

    if ip:
        ips = ip.split('.')[:length]
        ips.extend(['0'] * (4 - length))
        ip = '.'.join(ips)

    return ip or '0.0.0.0'

def env_format(env):
    "从env信息中提取对统计有用的数据"
    return storage(
            # ip 地址
            ip = real_ip(env),
            # 来源地址
            referer = env.get('HTTP_REFERER', None),
            # 当前时间
            time = datetime.now().strftime('%Y%m%d'),
        )

def attr_filter(obj, attrs):
    "属性过滤"
    for attr in attrs:
        if attr in obj:
            del obj[attr]
    return obj

def randint(a, b):
    return random.randint(a, b)

def parse_coordinates(text):
    """
    将字符串解析为坐标
    text的格式必须是纬度在前，经度在后
    lat, lng
    """
    if ',' not in text:
        return False

    return map(lambda x: floatval(x), text.split(','))

def hex_to_id(id_text):
    "将ID的16进制字符串转换为整型"
    if id_text:
        try:
            id_text = decrypt(binascii.a2b_hex(id_text))
            return intval(id_text[:len(id_text) - 1]) \
                    if id_text else 0
        except:
            return 0

    return 0

def id_to_hex(id):
    "将ID的整数类型转换为16进制字符串"
    if isinstance(id, (int, long)):
        id = str(id)
    id += '|'
    return binascii.b2a_hex(encrypt(id))

def floatval(text, value = 0.):
    "安全的浮点型转换"
    text = str(text) if isinstance(text, unicode) else text
    try:
        return float(text) if text else value
    except ValueError as e:
        return value

def intval(text, value = 0):
    "安全的整型转换"
    if isinstance(text, (int, long, bool)):
        return int(text)
    if isinstance(text, (float, decimal.Decimal,)):
        return int(text)
    if isinstance(text, (str, unicode,)):
        try:
            text = text.replace(',', '')
            return int(text) if text else value
        except ValueError as e:
            return value

    return value


def sql_escape(text):
    "转移sql的非法字符"
    return text.replace("'", r"\'")

def is_upload_file(field):
    "判断给定对象是否为上传的文件"
    from cgi import FieldStorage
    return isinstance(field, FieldStorage) and bool(field.filename)

def service_mail(recvs, subject, content):
    """
    发送服务邮件（使用service@xunbaotu.com）
    @recvs as [storage(name, email)], 接受邮件的人
    @subject as str, 邮件标题
    @content as str, 邮件内容
    """
    return sendmail('=?UTF-8?B?%s?= <hi@dieyouji.com>' % base64_encode('蝶游计')
            , recvs
            , subject
            , content)

def sendmail(sender, recvs, subject, content):
    """
    发送邮件
    @sender as str, 发送人的邮件地址
    @recvs as [storage(name, email)], 接受邮件的人
    @subject as str, 邮件标题
    @content as str, 邮件内容
    """
    if not recvs:
        # 如果接受人无效
        return False
    # 设置邮件发送的账户
    web.config.smtp_username = email.Utils.parseaddr(sender)[1]
    # 编码标题，避免某些邮箱乱码
    subject = '=?UTF-8?B?%s?=' % base64.b64encode(subject)
    try:
        # 发送邮件
        web.sendmail(sender, recvs, subject, content
                , headers = ({
                        'User-Agent': 'Dieyouji.com Mail Server',
                        'X-Mailer': 'Dieyouji.com Mail MIA',
                        'Content-Type': 'text/html',
                        }
                    ))
        return True
    except:
        # 报错，发送失败
        raise
        return False

def urldecode(text):
    return urllib.unquote(str(text))

def urlencode(text):
    return urllib.quote(text.encode('utf-8') \
            if isinstance(text, unicode) else text)

INT_RE = re_compile(ur'^\d+$', re.IGNORECASE)
def is_integer(text):
    "给定文本是否是一个整数字符串"
    return text is not None and bool(INT_RE.match(text))

def cmp_i(lhs, rhs):
    "忽略大小写比较"
    return cmp(lhs.lower(), rhs.lower())

def passwd_encrypt(text, pubkey):
    "将密码加密为服务端接口能够处理的格式"
    if text:
        try:
            return base64_encode(rsa_encrypt(str(text), pubkey))
        except:
            return False
    return False

def passwd_decrypt(text, prikey):
    "将客户端传递上来的密码密文转换为明文"
    if text:
        try:
            return rsa_decrypt(base64_decode(text), prikey)
        except:
            return False
    return False

# TODO: 获取des对象
def _des():
	return des('%K3%j9t{', CBC, '\2\0\1\5\1\2\1\2', pad=None, padmode=PAD_PKCS5)

# TODO: 加密给定字符串
def encrypt(src):
	return src and _des().encrypt(src.encode('utf-8')) or None

# TODO: 解密给定字符串
def decrypt(src):
	try:
		return src and _des().decrypt(src).decode('utf-8') or None
	except:
		return None

def create_media_part(id):
    """
    根据给定id，创建媒体文件路径的关键部分
    """
    # 完整的媒体文件长度
    ret = '000000000'
    # 获取id长度
    length = len(str(id))
    # 长度若不够，补位
    if length < len(ret):
        # 给id前面补0，直至9位
        ret = '%s%s' % (ret[:-length], id)
        # 从左至右，每3位一级目录

    # 000/000/001
    return '%s/%s/%s' % (ret[:3], ret[3:6], ret[6:len(ret)])

def public_key_to_hex(pubkey):
    # 将公钥转换为16进制的字符串
    # 便于传递
    if isinstance(pubkey, (str, unicode,)):
        pubkey = rsa.PublicKey.load_pkcs1(pubkey)

    return hex(pubkey.n)[2:-1]

def rsa_decrypt_from_hex(text, prikey):
    if text:
        try:
            # 将十六进制数据转换为rsa的加密结果
            # 私钥格式转换
            # 进行解密
            return rsa_decrypt(binascii.a2b_hex(text), prikey)
        except:
            return False
    return False

def rsa_encrypt_to_hex(text, pubkey):
    if text:
        try:
            # 再转换加密结果为16进制字符串
            return binascii.b2a_hex(rsa_encrypt(text, pubkey))
        except:
            return False
    return False

PASSWD_RE = re.compile(ur'^.{6,16}$', re.IGNORECASE)
def is_valid_passwd(text):
    """
    判断给定字符串是否是一个有效的密码
    1) 6-16位字符
    """
    if text:
        if not isinstance(text, unicode):
            text = unicode(text, 'utf-8')
        return PASSWD_RE.match(text)
    return False

LOGINNAME_RE = re.compile(ur'^[A-Za-z]{1}[0-9A-Za-z_]{5,16}$', re.IGNORECASE)
def is_valid_loginname(text):
    """
    判定给定字符串是否一个有效的登录名
    """
    if text:
        if not isinstance(text, unicode):
            text = unicode(text, 'utf-8')
        return bool(LOGINNAME_RE.match(text))
    return False

NAME_RE = re.compile(ur'^[\u4e00-\u9fa5\w]{2,24}$', re.IGNORECASE)
def is_valid_name(text):
    """
    判断给定字符串是否是一个有效的用户昵称
    1) 中文
    2) 英文
    3) 数字
    4) 下划线
    5) 4-24个字符
    """
    if text:
        if not isinstance(text, unicode):
            text = unicode(text, 'utf-8')
        return bool(NAME_RE.match(text))
    return False

URL_RE = re_compile(r'^(?:http|https)\://.+', re.IGNORECASE)
def is_url(src):
    "给定字符串是否是有效的URL"
    if src:
        return bool(URL_RE.match(src))

    return False

# TODO: 判断制定字符串是否是正确的Email地址格式
def is_email(src):
    if src:
        p = re_compile(ur'^([a-z0-9_\.\-\+]+)@([\da-z\.\-]+)\.([a-z\.]{2,6})$', re.IGNORECASE)
        return bool(p.match(src))
    return False

def rsa_decrypt(text, prikey):
    if isinstance(prikey, (str, unicode,)):
        # 如果传入的私钥是一个字符串
        # 那么将其转换为私钥对象
        prikey = rsa.PrivateKey.load_pkcs1(prikey)

    # 返回解密后的结果
    return rsa.decrypt(text, prikey)

def rsa_encrypt(text, pubkey):
    if isinstance(pubkey, (str, unicode,)):
        # 如果传入的公钥是一个字符串
        # 那么将其转换为公钥对象
        pubkey = rsa.PublicKey.load_pkcs1(pubkey)

    # 返回加密后的结果
    return rsa.encrypt(str(text), pubkey)

def base64_encode(text):
    if isinstance(text, unicode):
        text = text.encode('utf-8')

    return base64.b64encode(text)

def base64_decode(text):
    if isinstance(text, unicode):
        text = text.encode('utf-8')
        text = text.replace(' ', '+')

    return base64.b64decode(text)

def sha1(text):
    "给定字符串进行sha1加密"
    if text:
        if isinstance(text, unicode):
            text = text.encode('utf-8')

        return hashlib.sha1(text).hexdigest()

    return ''

def md5(text):
    if text:
        if isinstance(text, unicode):
            text = text.encode('utf-8')

        return hashlib.md5(text).hexdigest()

    return ''

def rs_to_dict(rs, nfield, vfield):
    """
    RecordSet 对象转换为 dict 对象
    @rs as RecordSet, 要转换为dict的对象
    @nfield as string, 作为key的字段名
    @vfield as string, 作为value的字段名
    """
    raw = storage()
    map(lambda x: raw.__setattr__(x[nfield], x[vfield]), rs)
    return raw

def bubble_sort(lst):
    "冒泡排序"
    l = len(lst)
    for i in xrange(0, l - 1):
        swap = False
        for j in xrange(0, l - i - 1):
            if lst[j] > lst[j + 1]:
                lst[j], lst[j + 1] = lst[j + 1], lst[j]
                swap = True
        if not swap:
            break
    return lst

class PagerBak:
    def __init__(self, url, total_count, page_size = 20, cur_page = 1, attach_css = ''):
        self.url = url#转向地址
        self.attach_css = attach_css
        self.total_count = total_count#总条目数
        self.page_size = page_size#每页条目数
        self.cur_page = cur_page#当前页数
        self.page_count,tail = divmod(self.total_count, self.page_size)#获取总分页数
        if tail > 0:
            self.page_count += 1

        #结果集
        self.pages = []

    def render_full(self
            , warpper = '<div class="row mb0"><div class="col-md-12">%(left)s%(right)s</div></div>'
            , left_warpper = '<div class="pull-left">%s</div>'
            , right_warpper = '<div class="pull-right"><div class="pagination">%s</div></div>'
            , entity_name = '记录'
            , entity_text = '共 %(total_count)s 个%(entity_name)s，每页 %(page_size)s 个'):
        """
        渲染完整的html
        @warpper as str, 整体包装器
        @left_warpper as str, 左边区域包装器
        @right_warpper as str, 右边区域包装器
        """
        left = left_warpper % str(self.__str__())
        right = right_warpper % entity_text % {
                        'entity_name':  entity_name,
                        'total_count':  self.total_count,
                        'page_size':    self.page_size,
                    }

        self.pages = []
        return warpper % { 'left': left, 'right': right, }

    def __str__(self):
        if self.cur_page > 1:
            self.pages.append('<li><a href="%s">&laquo;</a></li>' %(self.url %(self.cur_page-1)))
        else:
            self.pages.append('<li class="disabled"><a href="javascript:;">&laquo;</a></li>')

        if self.cur_page <= 5:
            limit_s = 1
        else:
            limit_s = self.cur_page - 4

        if self.page_count >= self.cur_page + 5:
            limit_e = self.cur_page + 5
        else:
            limit_e = self.page_count
            if self.cur_page >= 10:
                limit_s = self.cur_page - 9

        for i in xrange(limit_s,limit_e + 1):
            if self.cur_page == i:
                self.pages.append('<li class="active"><a href="javascript:;">%s <span class="sr-only">(current)</span></a></li>' % \
                                self.cur_page)
            else:
                self.pages.append('<li><a href="%s">%s</a></li>' % (self.url % i, i))
        if self.cur_page < self.page_count:
            self.pages.append('<li><a href="%s">&raquo;</a></li>' % (self.url % (self.cur_page + 1)))
        else:
            self.pages.append('<li class="disabled"><a href="javascript:;">&raquo;</a></li>')

        return '<div class="pagination %s">%s</div>' % (self.attach_css, ''.join(self.pages))

class Pager:
    def __init__(self, url, total_count, page_size = 20, cur_page = 1, attach_css = ''):
        self.url = url#转向地址
        self.attach_css = attach_css
        self.total_count = total_count#总条目数
        self.page_size = page_size#每页条目数
        self.cur_page = cur_page#当前页数
        self.page_count,tail = divmod(self.total_count, self.page_size)#获取总分页数
        if tail > 0:
            self.page_count += 1

        #结果集
        self.pages = []

    def render_full(self
            , page_total='<div class="ui-page-total">%s</div>'
            , warpper = u'<div class="ui-page">%(left)s%(center)s%(right)s</div>'
            , left_warpper = u'<div class="ui-page-total">%s</div>'
            , center_warpper=u'<div class="ui-page-list">%s</div>'
            , right_warpper = u'<div class="ui-page-jump"><form class="_pager_form" action="%s" method="get">'
                              u'<input type="text" name="page" class="inp _pager_num">'
                              u'<input type="hidden" class="_page_count" value="%s"/>'
                              u'<input type="button" class="btn _pager_submit_btn" value="GO">'
                              u'</form></div>'
            , entity_name = u'记录'
            , entity_text = u'共 %(total_count)s 个%(entity_name)s，每页 %(page_size)s 个'):
        """
        渲染完整的html
        @warpper as str, 整体包装器
        @left_warpper as str, 左边区域包装器
        @right_warpper as str, 右边区域包装器
        """
        if isinstance(entity_name, str):
            entity_name = entity_name.decode('utf-8')
        if isinstance(entity_text, str):
            entity_text = entity_text.decode('utf-8')

        center = center_warpper % self.__str__()
        left = left_warpper % entity_text % {
                        'entity_name':  entity_name,
                        'total_count':  self.total_count,
                        'page_size':    self.page_size,
                    }
        right = right_warpper % (self.url % 'x', self.page_count)

        return warpper % { 'left': left, 'center': center, 'right': right }

    def __str__(self):
        if self.cur_page > 1:
            self.pages.append(u'<a href="%s">上一页</a>' %(self.url % (self.cur_page-1)))
        else:
            self.pages.append(u'<a href="javascript:;">上一页</a>')

        if self.cur_page <= 5:
            limit_s = 1
        else:
            limit_s = self.cur_page - 4

        if self.page_count >= self.cur_page + 5:
            limit_e = self.cur_page + 5
        else:
            limit_e = self.page_count
            if self.cur_page >= 10:
                limit_s = self.cur_page - 9

        for i in xrange(limit_s,limit_e + 1):
            if self.cur_page == i:
                self.pages.append(u'<a href="javascript:;" class="on">%s</a>' % \
                                self.cur_page)
            else:
                self.pages.append(u'<a href="%s">%s</a>' % (self.url % i, i))
        if self.cur_page < self.page_count:
            self.pages.append(u'<a href="%s">下一页</a>' % (self.url % (self.cur_page + 1)))
        else:
            self.pages.append(u'<a href="javascript:;">下一页</a>')

        return u'<div class="pagination %s">%s</div>' % (self.attach_css, ''.join(self.pages))

    def render_simple(self):
        if self.cur_page > 1:
            self.pages.append(u'<a href="%s"><</a>' %(self.url %(self.cur_page-1)))
        else:
            self.pages.append(u'<a href="javascript:;"><</a>')

        if self.cur_page <= 5:
            limit_s = 1
        else:
            limit_s = self.cur_page - 4

        if self.page_count >= self.cur_page + 5:
            limit_e = self.cur_page + 5
        else:
            limit_e = self.page_count
            if self.cur_page >= 10:
                limit_s = self.cur_page - 9

        for i in xrange(limit_s,limit_e + 1):
            if self.cur_page == i:
                self.pages.append(u'<a href="javascript:;" class="on">%s</a>' % \
                                self.cur_page)
            else:
                self.pages.append(u'<a href="%s">%s</a>' % (self.url % i, i))
        if self.cur_page < self.page_count:
            self.pages.append(u'<a href="%s">></a>' % (self.url % (self.cur_page + 1)))
        else:
            self.pages.append(u'<a href="javascript:;">></a>')

        return u'<div class="pagination %s">%s</div>' % (self.attach_css, ''.join(self.pages))

class Input(object):
    def __init__(self, params = None, **kwargs):
        self.params = kwargs
        self.params.update(params or web.input())

    def __getitem__(self, name):
        return self._param(name)

    def __getattr__(self, name):
        return self._param(name)

    def __setitem__(self, name, value):
        self.params[name] = value

    def hex_id(self, name):
        """
        获取给定参数，将16进制转换为int
        :return:
        """
        val = self.get(name)
        if val:
            return hex_to_id(val)

        return 0

    def json(self, name, default = None):
        """
        获取给定参数的
        :param name:
        :param default:
        :return:
        """
        val = self.get(name)
        if val:
            return json_loads(val) or default

        return default

    def split(self, name, sep = ',', func = None, filter_func = None):
        """
        分割给定参数的值
        :param name: 参数名
        :param sep: 分隔符
        :return:
        """
        val = self.get(name)
        if val:
            result = [func(v) for v in val.split(sep)] if callable(func) else val.split(sep)
            if callable(filter_func):
                return filter(filter_func, result)

            return result

        return None

    def equals(self, name, rhs):
        """
        判定给定参数值是否与给定值相等
        :param name: 参数名
        :param rhs: 要比较的值
        :return: bool
        """
        return self.get(name) == rhs

    def int(self, name, default = 0):
        return intval(self._param(name), default)

    def boolean(self, name, default = 'false'):
        return self._param(name, default).lower() in ('true', '1',)

    def float(self, name, default = 0):
        return floatval(self._param(name), default)

    def get(self, name, default = None):
        return self.params.get(name, default)

    def date2int(self, name, fmt = '%Y-%m-%d'):
        "将传入的日期转换为整型"
        value = self._param(name)
        if value:
            try:
                d = datetime.strptime(value, fmt)
                return intval(d.strftime('%Y%m%d'))
            except ValueError as ve:
                return 0
        return 0

    def date(self, name, fmt = '%Y-%m-%d'):
        "将给定日期字段转换为日期对象"
        return str2date(self._param(name), fmt)

    def range(self, name, sep = ','):
        "获取范围参数"
        value = self._param(name)
        if value and isinstance(value, (str, unicode,)):
            values = map(lambda x: intval(x, -1), value.split(','))
            sorted(values)

            return values[0], values[-1]

        return None

    def multi(self, name, sep = ','):
        "获取多值参数"
        value = self._param(name)
        if value and isinstance(value, (str, unicode,)):
            return filter(lambda x: x > -1
                    , [intval(x, -1) for x in value.split(sep)])

        return None

    def _param(self, name, default = None):
        "获取参数"
        return self.params[name] if self.params and name in self.params else default

    def _page(self):
        "获取page参数"
        return max(self.int('page', 1), 1)

    page = property(_page)

    def _get_limit(self):
        "获取limit参数"
        return max(self.int('limit', 20), 1)

    def _set_limit(self, v):
        "设置limit参数"
        self.params['limit'] = v

    limit = property(_get_limit, _set_limit)

    def _offset(self):
        "获取offset参数"
        return (self.page - 1) * self.limit

    offset = property(_offset)

    def serialize(self, exclude = ['page', 'limit'], escape = True):
        query = urllib.urlencode({k: v.encode('utf-8') if isinstance(v, unicode) else v for k, v in self.params.iteritems() if k not in exclude})
        if escape:
            query = query.replace('%', '%%')
        return query

if __name__ == '__main__':
    pass
