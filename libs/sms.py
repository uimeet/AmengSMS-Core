# coding=utf-8

"""
封装短消息发送
"""

import urllib
from web.utils import storage

import http
import utils

# 消息模板
MESSAGES = storage(

)
# 聚合数据的消息模板id
TEMPLATE = storage(
    # 注册验证码
    REGISTER_CODE   = 7255,
    # 安全验证码
    SAFE_CODE       = 7256,
)

class NotSupported(Exception):
    pass

class SMSBase(http.HttpRequest):
    "短信接口基类"
    #def __init__(self, config):
    #    self.config = config

    def make_url(self):
        "创建接口的URL地址"
        raise NotSupported('Function make_url not supported')

    def make_data(self):
        "创建提交到接口的数据"
        raise NotSupported('Function make_data not supported')

    def send(self, mobile, message):
        raise NotSupported('Function send not supported')

    def receive(self):
        raise NotSupported('Function receive not supported')

class LKSMS(SMSBase):
    "凌凯短信接口"
    def make_url(self):
        "创建接口地址"
        return 'http://sdk.mobilesell.cn/ws/BatchSend.aspx'

    def make_data(self):
        return {
            'CorpID': 'CQLKJ0003964',
            'Pwd': 'Ohqi!%(#%&iqhO',
            'SendTime': ''
        }

    def send(self, mobile, content):
        payload = self.make_data()
        payload['Mobile'] = mobile
        # 内容有效
        if content:
            try:
                content = content.encode('cp936')
            except:
                content = content.encode('GB18030')

            payload['content'] = content
            resp = self.load(self.make_url(), data = payload, method = 'post')

            return utils.intval(resp.text) == 1

        return False

    def send_message(self, mobile, message_key, values):
        return self.send(mobile, self.msg_fmt(MESSAGES.get(message_key), values))

    def msg_fmt(self, content, values):
        "消息格式化"
        return content % values

class JHSMS(SMSBase):
    "聚合数据短信接口"
    def make_url(self):
        "创建接口地址"
        return 'http://v.juhe.cn/sms/send?key=d875f95f5f439265d555b37e2c060515&%s'

    def send(self, mobile, template_id, **template_values):
        """
        发送短信
        @mobile as str, 手机号
        @template_id as int 已通过审核的短信模板id
        @template_values as dict 模板变量值集合
        @return as bool 发送是否成功
        """
        url = self.make_url() % urllib.urlencode({
            'mobile': mobile,
            'template_id': template_id,
            'template_values': self.format_values(template_values)
        })
        resp = self.load(url)
        # 聚合返回数据为json格式
        result = resp.json()

        return result['error_code'] == 0

    def send_regcode(self, mobile, code):
        "发送注册验证码"
        return self.send(mobile, TEMPLATE.REGISTER_CODE, code = code)

    def send_safecode(self, mobile, code):
        "发送安全验证码"
        return self.send(mobile, TEMPLATE.SAFE_CODE, code = code)

    def format_values(self, values):
        """
        格式化模板的变量值集合
        """
        return ''.join([ '#%s#=%s' % (k, v.encode('utf-8')) for k, v in values.iteritems() ])

manager = LKSMS()