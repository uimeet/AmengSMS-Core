#!/usr/bin/env python
# encoding: utf-8

import web
import settings

class Skin(object):
    def __init__(self, name):
        # 皮肤名称
        self.name = name
        self._init_setting()

    def _init_setting(self):
        # 主题的静态文件的根路径
        self.static_root = '%s/static/skins/%s' % (settings.STATIC_FILE_DOMAIN, self.name)
        # 模板渲染器
        self.render = web.template.render('static/skins/%s/templates/' % self.name)

class SkinManager(object):
    def __init__(self, skin_config):
        self.skin_config = skin_config
        self.skins = {}
        # 静态文件根目录
        self.static_root = '%s/static' % settings.STATIC_FILE_DOMAIN

    def __getattr__(self, pos):
        return self.skins.get(pos, self._make(pos))

    def _make(self, pos):
        "生成一个Skin实例"
        skin_name = self.skin_config.get(pos, None)
        assert(skin_name)

        self.skins[pos] = Skin(skin_name)
        return self.skins[pos]

manager = SkinManager(settings.SKINS)
