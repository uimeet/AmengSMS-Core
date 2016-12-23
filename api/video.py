# coding=utf-8

import web
from web.utils import storage

from core import utils
from core.libs import db

import enums
import task

class Video(storage):
    def __init__(self, **kwargs):
        super(Video, self).__init__(**kwargs)

        if isinstance(self.status, (int, long)):
            self.status = enums.Video.Status.find(self.status)

class VideoDAL(object):
    "视频相关数据库接口"

    @staticmethod
    def md5load(md5):
        "返回给定md5的视频信息"
        if utils.is_md5(md5):
            rs = db.manager.slave_media.select('video', where='md5 = $md5', vars=locals())
            return Video(**rs[0]) if rs else None

        return None

    @staticmethod
    def load(vid):
        "加载给定视频记录"
        rs = db.manager.slave_media.select('video', where='id = $vid', vars=locals())
        return Video(**rs[0]) if rs else None

    @staticmethod
    def exists(md5, mdb = None):
        "查询给定视频是否存在"
        mdb = mdb or db.manager.slave_media
        rs = mdb.query("""
                SELECT EXISTS(SELECT NULL FROM video WHERE md5 = $md5) AS ext;
                """, vars = locals())
        return rs[0].ext == 1

    @staticmethod
    def add(params):
        """
        添加一条视频记录
        @params as storage, 参数列表
        @queued as bool, 是否添加到视频处理队列
        """
        mdb = db.manager.master_media
        with mdb.transaction():
            # 获取视频记录
            v = VideoDAL.md5load(params.md5)
            # 视频不存在才新增
            if not v:
                vid = mdb.insert('video',
                        title = params.name,
                        date_created = web.SQLLiteral('UNIX_TIMESTAMP()'),
                        extension = utils.extension(params.name),
                        content_type = params.content_type,
                        size = params.size,
                        md5 = params.md5,
                        status = enums.Video.Status.Pending.value,
                        length = 0)
                if vid > 0:
                    mdb.insert('video_raw', video_id = vid, server = params['server'], path = params['path'])
                    # 添加视频上传的事件任务
                    task.Task.create(enums.Task.Type.VideoUploaded,
                                     type_id = vid,
                                     tail_num=int(params['server']))

                return {
                    'id': vid,
                    'title': params.name,
                    'extension': utils.extension(params.name),
                    'content_type': params.content_type,
                    'size': params.size,
                    'md5': params.md5,
                }

            return v