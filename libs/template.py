# coding=utf-8

import web
from web.template import Template

def init(libs):
    "初始化模板"
    assert(isinstance(libs, dict))

    # 初始化变量
    Template.globals['debug'] = web.config.debug

    Template.globals['round'] = round
    Template.globals['str'] = str
    Template.globals['float'] = float

    Template.globals.update(libs)