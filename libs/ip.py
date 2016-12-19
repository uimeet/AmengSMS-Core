# coding=utf-8

from core import utils
import http
import cache

import settings


def _ip2location(ip):
    """
    将 ip 转换为位置信息
    :param ip: ip 地址
    :return:
    """
    assert(ip)
    try:
        resp = http.GET(settings.JUHE.IP.URL % (settings.JUHE.IP.KEY, ip,))
        data = resp.json()
        if data and data['resultcode'] == '200':
            return data['result']
    except:
        pass

    return None

def location(ip = None):
    """
    获取给定IP地址的位置信息,如果不提供
    :param ip: 要获取位置信息的 ip 地址
    :return:
        返回位置信息的json格式
        {
            "resultcode":"200",
            "reason":"Return Successd!",
            "result":{
                "area":"辽宁省沈阳市",
                "location":"联通"
            },
            "error_code":0
        }
    """
    # ip的文本形式
    ip = ip or utils.real_ip()
    if ip > 0:
        loc = cache.manager.get(ip)
        if not loc:
            loc = _ip2location(ip)
            if loc:
                # 缓存此次查询
                cache.manager.set(ip, loc, seconds = 3600)

        return loc or {}

    return {}

