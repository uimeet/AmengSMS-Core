# coding=utf-8


from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex


# 基础密钥
KEY = 'IamTianzhen82618'
# 加密模式
MODE = AES.MODE_CBC

def decrypt(text, key_postfix = None, mode = MODE):
    """
    解密函数
    解密后去掉补足的空格
    """
    key = KEY if key_postfix is None else (KEY[:len(KEY) - len(key_postfix)] + key_postfix)

    cryptor = AES.new(key, mode, b'1982061819820618')
    try:
        decoded = cryptor.decrypt(a2b_hex(text))
        if decoded:
            return decoded.rstrip('\0')
    except Exception as ex:
        print 'ERROR:', ex, 'for', text

    return None

def encrypt(text, key_postfix = None, mode = MODE):
    """
    加密函数
    text 不足16位就用空格不足到16位，
    如果大于16而不是16的倍数，补足为16的倍数
    """
    if isinstance(text, unicode):
        text = text.encode('utf-8')

    key = KEY if key_postfix is None else (KEY[:len(KEY) - len(key_postfix)] + key_postfix)
    cryptor = AES.new(key, mode, b'1982061819820618')
    # 被加密字符串的长度
    count = len(text)
    if count < 16:
        text += ('\0' * (16 - count))
    elif count > 16:
        text += ('\0' * (16 - (count % 16)))

    return b2a_hex(cryptor.encrypt(text))


if __name__ == '__main__':
    import sys
    e = encrypt('田真') #加密
    d = decrypt(e) #解密
    print "加密:",e
    print "解密:",d