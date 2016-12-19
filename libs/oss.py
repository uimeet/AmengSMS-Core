# coding=utf-8

import sys

import requests

from core import utils
import settings

from qiniu import Auth, put_data

q = Auth(settings.QINIU.AK, settings.QINIU.SK)


def refresh_cache(resource_id, prefix = '', postfix = '', extension = '.jpg'):
    """
    刷新给定资源的缓存
    :param resource_id: 资源id
    :param prefix: 前缀
    :param extension: 资源文件扩展名
    :return:
    """

    url = utils.create_media_part(resource_id)
    if prefix and not prefix.endswith('/'):
        prefix += '/'
    if postfix and not postfix.endswith('/'):
        postfix += '/'

    url = '%(prefix)s%(url)s%(postfix)s%(extension)s' % locals()
    # 生成最终要清除缓存的url
    url = '%s%s' % (settings.QINIU.URL_PREFIX, url)
    # API 地址
    api_url = 'http://fusion.qiniuapi.com/v2/tune/refresh'
    # POST 数据
    data = utils.json_dumps({ 'urls': [url] })
    # 生成access_token
    access_token = q.token_of_request(api_url, data, 'application/json')
    resp = requests.post(api_url, data = data, headers = {
        'Authorization': 'QBox %s' % access_token,
        'Content-Type': 'application/json',
    })
    result = { 'code': 500, 'error': 'Unknown error' }
    if resp.status_code == 200:
        result.update(resp.json())

    return result

def id_to_url(id, prefix = '', postfix = '', extension = '.jpg'):
    "将给定id转换为URL"
    assert(isinstance(id, (int, long,)))
    assert(id > 0)

    url = utils.create_media_part(id)
    return '%(prefix)s%(url)s%(postfix)s%(extension)s' % locals()

def data2qiniu(data, resource_id, prefix = ''):
    "将指定url的图片上传到七牛"
    assert(data);

    urlmd5 = id_to_url(resource_id)
    path = '%(prefix)s%(urlmd5)s' % locals()

    token = q.upload_token(settings.QINIU.BUCKET, path)

    ret, info = None, None
    # 错误已重试次数
    retry = 0
    while True:
        try:
            ret, info = put_data(token, path, data, mime_type = 'image/jpeg', check_crc = True)
            break
        except Exception, e:
            retry += 1
            if retry <= 3:
                print 'Upload file to Qiniu. %s/3' % retry
                continue
            else:
                raise e

    if ret['key'] != path:
        sys.stderr.write('UPLOAD ERROR: %s' % info)
        return False

    return path


def save_file_to_qiniu(code, fp, bucket_name = settings.QINIU.BUCKET, prefix = '', postfix = '', extension = '.jpg'):
    "保存文件到七牛"

    assert(isinstance(code, (int, long,)))
    assert(code > 0)

    path = id_to_url(code, prefix, postfix, extension)

    token = q.upload_token(bucket_name, path)


    data = fp.read()

    ret, info = None, None
    # 错误已重试次数
    retry = 0
    while True:
        try:
            ret, info = put_data(token, path, data, mime_type = 'image/jpeg', check_crc = True)
            break
        except Exception, e:
            retry += 1
            if retry <= 3:
                print 'Upload file to Qiniu. %s/3' % retry
                continue
            else:
                raise e

    if ret['key'] != path:
        sys.stderr.write('UPLOAD ERROR: %s' % info)
        return False

    return path