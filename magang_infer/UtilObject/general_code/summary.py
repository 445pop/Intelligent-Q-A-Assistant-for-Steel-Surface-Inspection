from datetime import datetime
import traceback
import time
from MyObject.Steel import Steel
from UtilObject.DatabaseUtil import MyDatabase
from MyObject.ProjectConfig import MySettings
from MyObject.ProjectConfig import Grade

from cryptography.fernet import Fernet
import base64


def compare_defect(x, y):
    if x['type'] < y['type']:
        return -1
    elif x['type'] > y['type']:
        return 1
    else:
        if x['camera_id'] < y['camera_id']:
            return -1
        elif x['camera_id'] > y['camera_id']:
            return 1
        else:
            if int(x['flow_id']) < int(y['flow_id']):
                return -1
            elif int(x['flow_id']) > int(y['flow_id']):
                return 1
            else:
                if x['y'] < y['y']:
                    return -1
                elif x['y'] > y['y']:
                    return 1
                else:
                    return 0


def decrypt_time(encrypted_time_b64, key):
    encrypted_time = base64.b64decode(encrypted_time_b64)
    fernet = Fernet(key)
    decrypted_time_bytes = fernet.decrypt(encrypted_time)
    decode_decry = decrypted_time_bytes.decode('utf-8')
    decrypted_time = datetime.strptime(decode_decry, '%Y-%m-%d')
    return decrypted_time


def get_run_state(decrypted_time):
    current_date = datetime.now()
    # 计算两个日期之间的天数差
    days_diff = (decrypted_time - current_date).days
    return days_diff >= 0


def summary(main_id, sys_setting,alarmCancelled,is_cpj=False):
    # 删除冗余 or 删除钢材缺陷生成新钢材缺陷
    # 重新评级不报警
    details = ""
    conclusion = ""
    logger = sys_setting.logger
    cfg_runner = sys_setting.cfg_runner
    actions = []
    database = MyDatabase(sys_setting)
    database.create_es()

    t_start = time.time()
    logger.info("summary begin {}".format(main_id))

    try:
        steel_info = database.get_batch_info_by_main_id(main_id)

        cu_defect_list = database.get_defects_by_main_id(main_id)

        # 图像数目
        pic_num = 0
        for cid in (cfg_runner['CameraOffset'].keys()):
            c_pic_len = database.get_max_flowid_by_main_id(main_id, cid) + 1
            pic_num += c_pic_len

        # 读取最新配置文件
        sys_setting.updata_appraise()
        # 判断运行状态 
        decrypted_time = decrypt_time(cfg_runner['end_time'], 'nB9aQF49fIvI6aNrmLD6v3hxb80v38uEYVIpC0p0oVY=')
        run_state = get_run_state(decrypted_time)
        if not run_state:
            logger.error('--------已到指定时间--------------')
        steel = Steel(main_id, sys_setting, cu_defect_list, steel_info)  # 想弄多线程
        steel.process_defect()

    except Exception as e:
        logger.error(traceback.format_exc())
        return
    
    try:
        logger.info("{}分析完开始报警，写数据库".format(main_id))
        if run_state:
            for info in steel.send_client_extra_info:
                message, defect = info
                if not is_cpj :
                    # 发送报警信息
                    sys_setting.post_client_data(database, "steel_defect", defect.id, defect.insert_time, message,
                                                 defect.main_id)

            for key in steel.image_defect_type_dict.keys():
                for defect in steel.image_defect_type_dict[key]:
                    _id = defect.pop('_id')
                    # logger.info("defect :" +str(defect)+"  ----   "+str(_id))
                    update_action = {
                        '_op_type': 'update',
                        '_index': cfg_runner['Database']['ES']['es_table'][1],
                        '_id': _id,
                        'doc': defect
                    }
                    actions.append(update_action)

        for key in steel.steel_defect_type_dict.keys():
            type_name = cfg_runner['Detect']['typeid_chinese'][key]
            for defect in steel.steel_defect_type_dict[key]:
                if not run_state:
                    defect['grade'] = '疑似'
                index_action = {
                    '_op_type': 'index',
                    '_index': cfg_runner['Database']['ES']['es_table'][2],
                    '_source': defect
                }
                actions.append(index_action)
                # if defect['grade'] == "报警" and run_state:
                #     if (key in cfg_runner['Conclusion']['typeid_merge']):  # 聚合缺陷
                #         # 向客户端发送报警信息
                #         message = '{}批次中, {:.2f}m处出现报警[{}]缺陷！\n'.format(
                #             str(main_id),
                #             round(defect['real_y'] / 1000, 2), 
                #             type_name)
                #         if not is_cpj :
                #             sys_setting.post_client_data(database, "steel_defect", defect['id'],
                #                                          str(defect['insert_time']), message, defect['main_id'])
                # if defect['grade'] == "报警" and run_state:
                #     if key == 0:
                #         # 漏清为报警时,记录评级
                #         if defect['surface_id'] == 1:
                #             surface = "西侧"
                #             details += "{}{}报警:窄面漏清率{}%\n".format(surface,type_name,defect['area_rate'])
                #         elif defect['surface_id'] == 2:
                #             surface = "上表"
                #             details += "{}{}报警:宽面漏清率{}%\n".format(surface,type_name,defect['area_rate'])
                #         elif defect['surface_id'] == 3:
                #             surface = "下表"
                #             details += "{}{}报警:宽面漏清率{}%\n".format(surface,type_name,defect['area_rate'])
                #         elif defect['surface_id'] == 4:
                #             surface = "东侧"
                #             details += "{}{}报警:窄面漏清率{}%\n".format(surface,type_name,defect['area_rate'])
                if key == 0:
                    if defect['surface_id'] == 1:
                        surface = "西侧"
                        details += "{}检出{}:窄面漏清率{:.2f}%\n".format(surface,type_name,defect['area_rate'])
                    elif defect['surface_id'] == 2:
                        surface = "上表"
                        details += "{}检出{}:宽面漏清率{:.2f}%\n".format(surface,type_name,defect['area_rate'])
                    elif defect['surface_id'] == 3:
                        surface = "下表"
                        details += "{}检出{}:宽面漏清率{:.2f}%\n".format(surface,type_name,defect['area_rate'])
                    elif defect['surface_id'] == 4:
                        surface = "东侧"
                        details += "{}检出{}:窄面漏清率{:.2f}%\n".format(surface,type_name,defect['area_rate'])
            conclusion += "-{}-:{}\n".format(key, len(steel.steel_defect_type_dict[key]))
        if run_state:
            finished = 1
            defect_img_ratio = 0  # 缺陷占比 图像比

            de_pic_num = 0
            for key in steel.image_defect_camera_flow_dict.keys():
                de_pic_num += len(steel.image_defect_camera_flow_dict[key])
            if pic_num > 0:
                defect_img_ratio = round((de_pic_num / pic_num) * 100, 2)

            if is_cpj:
                time.sleep(2)  # 重评级等待2s
            database.update_batch_from_mysql(steel.score, steel.grade, steel.steel_defect_total_ids_str,
                                             steel.steel_defect_num,
                                             steel.appraise_num[Grade(2).name], steel.appraise_num[Grade(3).name],
                                             steel.appraise_num[Grade(4).name],
                                             conclusion, details, finished, defect_img_ratio, main_id)
            #  '疑似', '警告', '报警'

            if str(steel.grade) == '较差':
                message = '{}批次质量较差！\n'.format(str(main_id))
                insert_time = datetime.now()
                if not is_cpj :
                    sys_setting.post_client_data(database, "steel_defect", '', str(insert_time), message,
                                                 str(steel.main_id))
            type_id_num_flag_dic = {}  # 出现重复插入amount解决

            for type_id in cfg_runner['Detect']['type_trans_a2c']:
                if type_id not in type_id_num_flag_dic.keys():
                    type_id_num_flag_dic[type_id] = True

                    defect_sum_num = steel.appraise_types_count[type_id][Grade(2).name] + \
                                     steel.appraise_types_count[type_id][
                                         Grade(3).name] + steel.appraise_types_count[type_id][Grade(4).name]
                    if defect_sum_num > 0:
                        # 各种类别的钢材缺陷数目
                        database.insert_steel_defect_amout(main_id, type_id,
                                                           steel.appraise_types_count[type_id][Grade(2).name],
                                                           steel.appraise_types_count[type_id][Grade(3).name]
                                                           , steel.appraise_types_count[type_id][Grade(4).name],
                                                           defect_sum_num)

        database.bulk_actions(actions)
    except Exception as e:
        logger.error(traceback.format_exc())

    logger.info("summary over----- {} --time {}---".format(main_id, time.time() - t_start))


if __name__ == '__main__':
    sys_setting = MySettings()
    main_id = '20240427072659'
    summary(main_id, sys_setting)
