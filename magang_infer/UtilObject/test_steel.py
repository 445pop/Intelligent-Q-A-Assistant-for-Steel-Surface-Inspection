import json
import multiprocessing
import queue
import traceback
import sys
from elasticsearch.helpers import bulk
from elasticsearch import Elasticsearch
from DBUtils.PooledDB import PooledDB
import pymysql
import time
from MyObject.ProjectConfig import MySettings
from MyObject.Steel import Steel

class MyDatabase():
    def __init__(self, sys_setting):
        self.cfg_runner = sys_setting.cfg_runner

        self.logger = sys_setting.logger
        # 创建数据库链接
        # self.es = self.create_es()
        # self.mysql_pool = self.create_mysql_pool()

    def create_es(self):
        self.es_host = self.cfg_runner['Database']['ES']['es_host']
        self.es_port = self.cfg_runner['Database']['ES']['es_port']
        self.es = Elasticsearch('http://' + str(self.es_host) + ':' + str(self.es_port))

    # 池化技术，注意连接数目，避免多线程同时调用
    def create_mysql_pool(self):
        self.mysql_host = self.cfg_runner['Database']['MYSQL']['mysql_host']
        self.mysql_port = self.cfg_runner['Database']['MYSQL']['mysql_port']
        self.mysql_pool = PooledDB(
            creator=pymysql,
            maxconnections=4,
            mincached=1,
            maxcached=4,
            blocking=True,
            maxshared=4,
            setsession=[],
            ping=1,
            host=self.mysql_host,
            port=int(self.mysql_port),
            user=self.cfg_runner['Database']['MYSQL']['mysql_user'],
            password=self.cfg_runner['Database']['MYSQL']['mysql_password'],
            database=self.cfg_runner['Database']['MYSQL']['mysql_database'],
        )

    def create_mysql(self):
        self.mysql_host = self.cfg_runner['Database']['MYSQL']['mysql_host']
        self.mysql_port = self.cfg_runner['Database']['MYSQL']['mysql_port']
        self.mysql = pymysql.connect(
            host=self.mysql_host,
            port=int(self.mysql_port),
            user=self.cfg_runner['Database']['MYSQL']['mysql_user'],
            password=self.cfg_runner['Database']['MYSQL']['mysql_password'],
            database=self.cfg_runner['Database']['MYSQL']['mysql_database'],
            # charset = 'utf8 -- UTF-8 Unicode'
        )

    def update_batch(self, main_id, real_width, real_length):
        # conn = self.mysql_pool.connection()
        conn = self.mysql

        try:
            with conn.cursor() as cursor:

                # 准备SQL语句
                sql = 'update batch set real_length = "{}",real_width = "{}" where main_id ' \
                      '= "{}" ;'.format(
                    real_length, real_width, main_id)
                # 执行SQL语句
                conn.ping(reconnect=True)
                cursor.execute(sql)

                # 执行完要提交
                conn.commit()
                self.logger.error("写入batch数据库成功：", main_id, real_width, real_length)
        except Exception as e:
            # 如果执行失败要回滚
            conn.rollback()
            self.logger.error(traceback.format_exc())
            self.logger.error("写入batch数据库失败：", main_id, real_width, real_length)
        conn.close()

    def get_appraise_cfg(self):
        try:
            # conn = self.mysql_pool.connection()
            conn = self.mysql
            cursor = conn.cursor()
            sql = 'select * from sysconfig order by id desc limit 1 '
            cursor.execute(sql)
            res = cursor.fetchone()
            cursor.close()
            conn.close()
            if not res:
                return
            return json.loads(res[2])
        except Exception as e:
            self.logger.error("Loading config failed!")
            self.logger.error(traceback.format_exc())
            return self.appraise_cfg

    def get_defects_by_main_id(self, main_id):
        table_name = self.cfg_runner['Database']['ES']['es_table'][1]
        return self.get_defects_by_table_name(main_id, table_name)

    def get_defects_by_table_name(self, main_id, table_name):
        content_size = 10000
        scroll_time = '1m'  # 设置滚动时间

        # 设置初始滚动请求
        body = {
            'query': {
                'term': {
                    'main_id': main_id
                }
            },
            'size': content_size
        }

        # 执行第一次滚动查询
        res = self.es.search(index=table_name, body=body, scroll=scroll_time)

        logs = []
        while True:
            # 获取当前滚动页面的文档
            hits = res['hits']['hits']
            if not hits:
                break

            # 将文档添加到日志列表中
            logs.extend(hits)

            # 执行下一次滚动查询
            scroll_id = res['_scroll_id']
            res = self.es.scroll(scroll_id=scroll_id, scroll=scroll_time)

        # 提取日志中的数据并返回
        ret = []
        for log in logs:
            log['_source']['_id'] = log['_id']
            ret.append(log['_source'])
        return ret

    def get_batch_time_from_mysql(self, main_id):
        try:
            # conn = self.mysql_pool.connection()
            with self.mysql as conn:
                cursor = conn.cursor()
                sql = 'SELECT * FROM batch WHERE main_id = %s ORDER BY start_time DESC LIMIT 1'
                cursor.execute(sql, (main_id,))
                res = cursor.fetchone()
                if not res:
                    return None
                # 将查询结果转换为字典，方便操作
                result_dict = {
                    "main_id": res[0],
                    "start_time": res[1],
                    "end_time": res[2]
                    # 继续添加其他字段...
                }
                return result_dict
        except Exception as e:
            self.logger.error("Loading config failed!")
            self.logger.error("Exception: %s", str(e))
            self.logger.error(traceback.format_exc())

    def update_batch_from_mysql(self, score, grade, defect_ids_str, defect_num, conclusion, details, main_id):
        try:
            
            conn = self.mysql
            with conn.cursor() as cursor:
                sql = 'update batch set score = %s, grade = %s, steel_defect_ids = %s, defect_num = %s, conclusion = %s, details = %s where main_id = %s;'
                cursor.execute(sql, (score, str(grade), defect_ids_str, defect_num, conclusion, details, main_id))
                conn.commit()
            self.logger.info("{} Mysql提交成功".format(main_id))
        except Exception as e:
            self.logger.error("数据库操作异常：\n" + str(e))
            self.logger.error(traceback.format_exc())
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def insert_steel_defect_amout(self, main_id, typeid, suspected_num, warn_num, alert_num, defect_sum_num):
        try:
            conn = self.mysql
            with conn.cursor() as cursor:
                sql = 'INSERT INTO steel_defect_amout (main_id, defect_type, suspected_num, warn_num, alert_num, defect_num) VALUES (%s, %s, %s, %s, %s, %s);'
                cursor.execute(sql, (main_id, typeid, suspected_num, warn_num, alert_num, defect_sum_num))
                conn.commit()
            self.logger.info("{} Mysql提交成功".format(main_id))
        except Exception as e:
            self.logger.error("数据库操作异常：\n" + str(e))
            self.logger.error(traceback.format_exc())
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def delete_steel_defect_amount(self, main_id):
        try:
            conn = self.mysql
            with conn.cursor() as cursor:
                # 使用参数化查询来避免SQL注入
                sql = 'DELETE FROM steel_defect_amout WHERE main_id = %s'
                cursor.execute(sql, (main_id,))
                conn.commit()
            self.logger.info("{} 的钢材缺陷记录已成功从数据库中删除".format(main_id))
        except Exception as e:
            self.logger.error("数据库操作异常：\n" + str(e))
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def delete_redu_delete(self, cur_main_id):
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "grade": '冗余存储'
                            }
                        },
                        {
                            "term": {
                                "main_id": cur_main_id
                            }
                        }
                    ]
                }
            }
        }
        try:
            #  with lock:
            result = self.es.delete_by_query(index=self.cfg_runner['Database']['ES']['es_table'][2], body=query,
                                             doc_type="_doc")
            self.logger.info('{} 冗余存储 is deleted '.format(cur_main_id))
            self.logger.info('delete result is {}'.format(result))

        except Exception as e:
            self.logger.error(traceback.format_exc())
            self.logger.error('error {} in main_id {}is not delete rongyu :'.format(e, cur_main_id))

    # 批处理进行es文档的增删改查
    def bulk_actions(self, actions):
        bulk(self.es, actions)


if __name__ == '__main__':
    sys_setting = MySettings()
    a = MyDatabase(sys_setting)
    a.create_es()
    main_id = '20240419171854'
    table_name = sys_setting.cfg_runner['Database']['ES']['es_table'][2]
    
    cu_defect_list = a.get_defects_by_main_id(main_id)
    
    steel = Steel(main_id, sys_setting, cu_defect_list[:1000])# 想弄多线程
    t1 = time.time()
    steel.process_defect()
    print(time.time() -t1)




