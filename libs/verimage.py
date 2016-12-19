#!/usr/bin/env python
# encoding: utf-8

import Image,ImageDraw,ImageFont
import random
import cStringIO
from core import utils

class RandomChar():
    """用于随机生成汉字"""
    @staticmethod
    def Unicode():
        val = random.randint(0x4E00, 0x9FBF)
        return unichr(val)

    @staticmethod
    def GB2312():
        head = random.randint(0xB0, 0xCF)
        body = random.randint(0xA, 0xF)
        tail = random.randint(0, 0xF)
        val = ( head << 8 ) | (body << 4) | tail
        str = "%x" % val
        return str.decode('hex').decode('gb2312')

class ImageChar():
    def __init__(self, fontColor = (0, 0, 0),
                    size = (100, 40),
                    fontPath = utils.filedir(__file__) + '/wqy.ttc',
                    bgColor = (255, 255, 255),
                    fontSize = 20):
        self.size = size
        self.fontPath = fontPath
        self.bgColor = bgColor
        self.fontSize = fontSize
        self.fontColor = fontColor
        self.font = ImageFont.truetype(self.fontPath, self.fontSize)
        self.image = Image.new('RGB', size, bgColor)

    def rotate(self):
        self.image.rotate(random.randint(0, 30), expand=0)

    def drawText(self, pos, txt, fill):
        draw = ImageDraw.Draw(self.image)
        draw.text(pos, txt, font=self.font, fill=fill)
        del draw

    def randRGB(self):
        return (random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255))

    def randPoint(self):
        (width, height) = self.size
        return (random.randint(0, width), random.randint(0, height))

    def randLine(self, num):
        draw = ImageDraw.Draw(self.image)
        for i in range(0, num):
            draw.line([self.randPoint(), self.randPoint()], self.randRGB())
        del draw

    def randLetter(self, num):
        gap = 5
        start = 0

        chars = []
        for i in range(0, num):
            char = utils.random_digits(1)
            chars.append(char)

            x = start + self.fontSize * i + random.randint(0, gap) + gap * i
            # 文字使用黑色
            self.drawText((x, random.randint(-5, 5)), char, (0, 0, 0))
            self.rotate()

        self.randLine(8)
        # 将生成的验证码内容加密存储到session中，有效时间5分钟
        return utils.session('__VI__', ''.join(chars))

    def randChinese(self, num):
        gap = 5
        start = 0

        chars = []
        for i in range(0, num):
            char = RandomChar().GB2312()
            chars.append(char)

            x = start + self.fontSize * i + random.randint(0, gap) + gap * i
            self.drawText((x, random.randint(-5, 5)), char, self.randRGB())
            self.rotate()

        self.randLine(18)
        # 将生成的验证码内容加密存储到session中，有效时间5分钟
        return utils.session('__VI__', ''.join(chars))

    def save(self, path):
        "将验证码图片保存为物理文件"
        self.image.save(path)

    def base64(self):
        "将验证码图片转换为base64格式"
        io = cStringIO.StringIO()
        try:
            self.image.save(io, 'PNG')
            return io.getvalue().encode('base64')
        finally:
            io.close()

    def render(self):
        "返回"
        io = cStringIO.StringIO()
        self.image.save(io, 'PNG')
        return io

    @staticmethod
    def check(text):
        "检查给定字符串是否与生成的验证码一致"
        vi = utils.session('__VI__')
        if vi:
            utils.delsession('__VI__')
            return vi.lower() == text.lower()
        return False

if __name__ == '__main__':
    ic = ImageChar(fontColor = (100, 211, 90))
    ic.randChinese(4)
    ic.save('1.png')
    print ic.base64()
