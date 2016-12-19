# coding=utf-8


import os

import random
import urllib2
import requests
from requests.exceptions import TooManyRedirects, ConnectionError
from web.utils import storage

import log
import settings

# 全局会话
SESSION = storage(
    # 请求次数
    length = 0,
    # 实际的会话实例
    session = None,
)

USER_AGENTS = (
    'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0;',
    'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    'Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1',
    'Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.8.131 Version/11.11',
    'Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Maxthon 2.0)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; TencentTraveler 4.0)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; The World)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SE 2.X MetaSr 1.0; SE 2.X MetaSr 1.0; .NET CLR 2.0.50727; SE 2.X MetaSr 1.0)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Avant Browser)',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
    'MQQBrowser/26 Mozilla/5.0 (Linux; U; Android 2.3.7; zh-cn; MB200 Build/GRJ22; CyanogenMod-7) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1',
    'Opera/9.80 (Android 2.3.4; Linux; Opera Mobi/build-1107180945; U; en-GB) Presto/2.8.149 Version/11.10',
)

class GenericError(Exception):
    "表示一个常规错误"
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)

class ScrapeHttpError(GenericError):
    def __init__(self, status_code, text):
        super(ScrapeHttpError, self).__init__('Scraping %s to error: %s' % (text, \
            status_code))


class HttpBase(object):
    """URL执行基类"""
    def __init__(self):
        self.host = ''
        self.referer = ''
        # 抓取到的数据
        self.data = None
        # 创建请求头
        self.headers = self.make_headers()
        self.server = os.getpid()

    def rand_ip(self):
        "生成随机ip"
        return '.'.join([str(random.randint(1, 255)) for x in xrange(4)])

    def make_response(self, request):
        """创建响应实例"""
        return urllib2.urlopen(request, timeout = 10)

    def make_headers(self):
        #ip = self.rand_ip()
        headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Charset': 'GBK,utf-8;',
                'Accept-Language': 'zh-CN,zh;q=0.8',
                'Accept-Encoding': 'gzip,deflate,sdch',
                'User-Agent': self.rand_useragnet(),
                #'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36',
                #'X-FORWARDED-FOR': ip,
                #'CLIENT-IP': ip,
            }
        if self.host:
            headers['Host'] = self.host
        if self.referer:
            headers['Referer'] = self.referer

        return headers

    def rand_useragnet(self):
        "获取一个随机的useragent"
        return random.sample(USER_AGENTS, 1)[0]

    def make_request(self, url, include_headers = True):
        """创建抓取请求实例"""
        return urllib2.Request(
                    url = url,
                    headers = self.headers if include_headers else None)

    def load(self, url, include_headers = True):
        while True:
            request = self.make_request(url, include_headers)
            try:
                httpresp = self.make_response(request)
                self.content = httpresp.read()

                httpresp.close()
                return self
            except Exception, e:
                if 'timed out' in str(e):
                    log.debug('TIME OUT RETRY')
                    continue

                raise e

    def scrape(self):
        return self.load(self.make_url())

    def make_url(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exp_type, exp, tb):
        """
        安全退出方法，保证处理器不会因为异常而意外中断
        @exp_type as Type, 异常的类型
        @exp as Exception的子类，异常实例
        @tb as traceback, 堆栈跟踪的实例
        """
        log.error(self.self.format_exception(exp_type, exp, tb))
        return True

class HttpRequest(HttpBase):
    """基于 requests 库的蜘蛛基类"""
    def __init__(self):
        super(HttpRequest, self).__init__()
        self._connection_reset_retry = 0

    def make_request(self, url, include_headers = True, force = False):
        """
        创建请求会话
        url as str, 要请求的url，本重载中该参数未使用
        include_headers as bool, 是否包含请求头
        force as bool, 是否强制使用旧的请求会话，而不检测回收策略
        """
        global SESSION
        # 某一会话在使用超过50次后重建
        if not SESSION.session or (force == False and SESSION.length >= 20):
            log.debug('Initializing http session after %s used.', SESSION.length)

            SESSION.session = requests.Session()
            SESSION.length = 0
            # 设置头
            if include_headers:
                SESSION.session.headers = self.headers

        # 递增使用次数
        SESSION.length += 1
        return SESSION.session

    def make_response(self, request):
        pass

    def success_response(self, response, status = []):
        return response.status_code == 200 or response.status_code in status

    def load(self, url
            , include_headers = True, method = 'get'
            , data = None
            , enable_proxy = False
            , proxy = 'default'
            , force = False):
        "加载给定地址"
        # 使用的代理
        proxies = None
        # 是否启用代理
        if settings.ENABLE_PROXY and enable_proxy:
            # 使用给定的代理配置
            proxies = settings.PROXIES[proxy]

        while True:
            request = self.make_request(url, include_headers, force = force)
            try:
                func = getattr(request, method)
                try:
                    resp = func(url, timeout = 5
                        , allow_redirects = True
                        , data = data
                        , proxies = proxies)

                    if resp.status_code < 200 or resp.status_code > 299:
                        raise ConnectionError('Not 200 (%s) status code found' % resp.status_code)

                    return resp
                except TooManyRedirects, e:
                    # 重定向次数太多
                    return storage(status_code = 1000, text = '')
                except ConnectionError, ce:
                    # 连接被重置
                    if self._connection_reset_retry >= 3:
                        raise ce

                    # 连接错误可以重试3次
                    # 超过3次则抛出异常
                    log.debug('%s, connection reset retry %s/3', str(ce), self._connection_reset_retry)
                    self._connection_reset_retry += 1
                    continue
            except Exception, e:
                if 'timed out' in str(e):
                    log.debug('Time out retry')
                    continue

                raise e

class ImageSpider(object):
    "图片抓取蜘蛛"
    def __init__(self, url, resource_id, prefix = ''):
        super(ImageSpider, self).__init__()
        # 抓取地址
        self.url = url
        # 存入七牛的前缀
        self.prefix = prefix
        if not self.prefix.endswith('/'):
            self.prefix += '/'

        # 资源id
        self.resource_id = resource_id
        # 抓取结果
        self.result = storage(success = False, message = u'抓取失败')

    def scrapy(self):
        "开始抓取"
        if self.url and self.prefix:
            resp = None
            try:
                resp = GET(self.url)
            except ConnectionError as ce:
                print ce

            if resp and resp.status_code >= 200 and resp.status_code < 300:
                print self.url
                return self.save(resp.content)
            else:
                self.result.message = 'Download error[%s]' % self.url
        elif not self.url:
            self.result.message = 'Image url is empty'
        elif not self.prefix:
            self.result.message = 'Config error[PREFIX]'

        return self.result

    def success(self, url):
        "抓取成功"
        prefix = settings.QINIU.URL_PREFIX
        if not prefix.endswith('/'):
            prefix += '/'

        self.result.update({
            'success': True,
            'message': u'抓取成功',
            'url': prefix + url,
        })

    def save(self, data):
        "保存图片"
        url = oss.data2qiniu(data, self.resource_id, prefix = self.prefix)
        if url:
            self.success(url)

        return self.result

req = HttpRequest()

def GET(url, headers = {}, enable_proxy = False):
    req.headers.update(headers)
    return req.load(url, enable_proxy = enable_proxy)

def POST(url, data = None, headers = {}, enable_proxy = False):
    req.headers.update(headers)
    return req.load(url, data = data, method = 'post', enable_proxy = enable_proxy)

def down_img(url, resource_id, prefix = ''):
    """
    下载图片到本地
    :param url: 远程图片的url地址
    :param resource_id: 资源内码
    :param prefix: 前缀
    :return:
    """
    spider = ImageSpider(url, resource_id, prefix)
    return spider.scrapy()
