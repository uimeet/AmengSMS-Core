# coding=utf-8

class ViewBase(object):
    "视图基类"

    def msg_fmt(self, messages, code):
        """
        格式化消息
        @messages as dict, 消息内容，格式 {
                'status': {
                    '0': 'danger:xxxxx',
                    '1': 'success:xxxxx',
                    ...
                },
                ...
            }
        @code as str, 消息码，格式：status-0
        @return as tuple(2), 项1 为error|success，项2为消息提示内容
        """
        assert (isinstance(messages, dict) and bool(messages))

        if code:
            codes = code.split('-')
            if len(codes) == 2:
                message = messages.get(codes[0], None)
                if message:
                    array = None
                    if isinstance(message, (str, unicode)):
                        array = message.split(':')
                    elif isinstance(message, dict):
                        message = message.get(codes[1], None)
                        if message:
                            array = message.split(':')

                    if array and len(array) == 2:
                        return array
        return None, None