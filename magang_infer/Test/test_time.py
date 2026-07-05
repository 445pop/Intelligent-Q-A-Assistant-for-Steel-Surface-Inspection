import traceback

conn = pymysql.connect(
            host='192.168.10.100',
            port=3306,
            user='root',
            password='123456',
            database='steeldetection',
            # charset = 'utf8 -- UTF-8 Unicode'
        )
eshost = '192.168.10.143'
es = Elasticsearch('http://' + eshost + ':9200')


def get_appraise_cfg():
    try:
        cursor = conn.cursor()
        sql = """  
        SELECT main_id,insert_time FROM batch  
        WHERE insert_time BETWEEN %s AND %s  
        """
        # 指定时间段，例如从'2023-01-01 00:00:00'到'2023-12-31 23:59:59'
        start_time = '2023-01-01 00:00:00'
        end_time = '2023-12-31 23:59:59'
        # 执行SQL查询
        cursor.execute(sql, (start_time, end_time))

        # 获取所有查询结果
        results = cursor.fetchall()
        return results
        # 打印结果
        # for row in results:
        #
        #     print(row['mainid'])
    except Exception as e:

        print(traceback.format_exc())
    finally:
        conn.close()  # 关闭数据库连接


def search_defects(main_id):
    logs = []
    # 按照main_id、时间查询
    body = {
        'query': {
            'term': {
                'main_id': main_id
            }
        },
        # 'sort': [{'flow_id': 'asc'}, {"_id": "desc"}],  # 以ziduan2为next_id，需要先对其进行排序
        'sort': [{'flow_id': 'asc'}],  # 以ziduan2为next_id，需要先对其进行排序
        'size': 1  # 指定当前页数据量
    }
    res = es.search(index='new_image_defect', body=body)  # 翻页取消使用filter
    logs += res['hits']['hits']
    ret = []
    for log in logs:
        log['_source']['_id'] = log['_id']
        ret.append(log['_source'])
    return ret

if __name__ == '__main__':
    get_appraise_cfg()



