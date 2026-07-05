import socket
import json
import threading
import time
import uuid  
import os
import re
import requests
from datetime import datetime
from MyObject.ProjectConfig import MySettings
from UtilObject.DatabaseUtil import MyDatabase
def extract_numbers_from_filename(filename):
    # 使用正则表达式匹配数字和它们之间的下划线
    pattern = r'\d+|[^_]+'
    match = re.findall(pattern, filename)
    # print(match)
    if match:
        return match
    else:
        raise ValueError("No numbers found in the filename.")
        #return None  # 或者你可以选择抛出一个异常：raise ValueError("No numbers found in the filename.")
def construct_json_object(image_id,image2_id,image3_id,image_url,surface_id,camera_id,cur_main_id,root_id, flow_id,steel_length,cu_mainid_start_time,cu_mainid_end_time,is_finish = None ):  
    """  
    构造一个模拟C++中JSON对象的Python字典，并返回其JSON字符串表示。  
      
    参数:  
    cur_main_id (str): 当前主ID。  
    flow_id (str): 流程ID。  
    camera_id (str): 相机ID。  
    left_edge (int): 左边界值。  
    right_edge (int): 右边界值。  
      
    返回:  
    str: JSON字符串表示的字典对象。  
    """  
      
    # 构造Python字典，模拟C++中的JSON对象  
    if is_finish is None:
        suanfa = {  
            "id": image2_id,  # 使用Python的uuid库生成UUID  
            "main_id": cur_main_id,  
            "flow_id": flow_id,  
            "image_url": image_url , 
            "type": 1,  
            "surface_id": surface_id,  
            "camera_id": camera_id,  
            "insert_time": str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))  ,  
            "has_steel": True,  
            "root_id":root_id,
            "left": 100,
            "has_top": True,  
            "has_bottom": True,  
            "width": 3072,  
            "height": 4096,  
            "is_delete": False,  
            "steel_length": steel_length,  
            "left_edge": 1,  
            "right_edge": 3072,  
            "signal": 0,  
            "image_id": image_id,
            "image2_id": image2_id,
            "image3_id": image3_id,
            "other0": "-41.329594",
            "other1": "-41.329594"
        }  
    else:
        
        suanfa = {"end_time":str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),"insert_time":cu_mainid_start_time,"main_id":cur_main_id,"signal":1}
    # 将Python字典转换为JSON字符串  
    json_str = json.dumps(suanfa, ensure_ascii=False, indent=4)  
      
    # 返回JSON字符串  
    return json_str 
# {'camera_id': 8, 'flow_id': 347, 'has_bottom': False, 'has_steel': False, 'has_top': False, 'height': 4096, 'id': 'FA3477F7-69EA-4B9C-B70F-4F023D6BD52C', 'image_id2': '7C6F6509-2C3F-48A5-BC35-AA7266CC84F7', 'image_url': 'D:\\grab_img\\20240515095558\\gray\\3_347.jpg', 'image_url2': 'D:\\grab_img\\20240515095558\\rgb\\3_347.jpg', 'insert_time': '2024-05-15T10:33:55', 'is_delete': False, 'left': 0, 'left_edge': 0, 'main_id': '20240515095558', 'right_edge': 4095, 'root_id': '112', 'signal': 0, 'steel_length': 136.736432, 'surface_id': 2, 'type': 1, 'width': 4096}

def send_message(main_id = '0'):
    t1 = time.time()
    keep_time = 100
    # 服务器地址和端口
    server_address = ('192.168.100.3', 9007)
    cu_mainid_start_time = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    # mainid = datetime.now().strftime("%Y%m%d%H%M%S")+'-Test'     
    mainid = datetime.now().strftime("%Y%m%d%H%M%S") 

    # database.insert_main_id(mainid,cu_mainid_start_time)
    a2c_message(mainid,cu_mainid_start_time,True)

    # 构造一个folder的list
    # /home/hongtai/yolo/depth_img/2023_11_2_13_43/192.168.9.2/gray/232090015B_149_two_3.jpg

    # al_images_head_d = r"/home/hongtai/yolo/depth_img/2023_11_2_13_43/192.168.9.2/gray"
    # al_images_head_u = r"/home/hongtai/yolo/depth_img/2023_11_2_13_43/192.168.9.2/gray"#算法图片路径
    # image_table_head_d = r'\\Grab1\192.168.100.1\img\2023_11_2_13_43\192.168.9.2\gray'
    # image_table_head_u = r'\\Grab1\192.168.100.1\img\2023_11_2_13_43\192.168.9.2\gray'#图像缺陷路径
    # caiji_2_al_head_d = r'D:\img\2023_11_2_13_43\192.168.9.2\gray'
    # caiji_2_al_head_u = r'D:\img\2023_11_2_13_43\192.168.9.2\gray'
    # al_images_head_d = r"/home/hongtai/yolo/depth_img/20240627114924/3d_img"
    # al_images_head_u = r"/home/hongtai/yolo/depth_img/20240627114924/3d_img"#算法图片路径
    # image_table_head_d = r'\\Grab1\192.168.100.1\img\20240627114924\3d_img'
    # image_table_head_u = r'\\Grab1\192.168.100.1\img\20240627114924\3d_img'#图像缺陷路径
    # caiji_2_al_head_d = r'D:\img\20240627114924\3d_img'
    # caiji_2_al_head_u = r'D:\img\20240627114924\3d_img' 
    #   
    # \\Grab1\192.168.100.1\img\20240628193151\gray
    
    # al_images_head_d = r"/home/hongtai/yolo/depth_img/20240628193151/gray"
    # al_images_head_u = r"/home/hongtai/yolo/depth_img/20240628193151/gray"#算法图片路径
    # image_table_head_d = r'\\Grab1\192.168.100.1\img\20240628193151\gray'
    # image_table_head_u = r'\\Grab1\192.168.100.1\img\20240628193151\gray'#图像缺陷路径
    # caiji_2_al_head_d = r'D:\img\20240628193151\gray'
    # caiji_2_al_head_u = r'D:\img\20240628193151\gray'   


    # \\Grab1\192.168.100.1\img\20240701144913\gray_img
    #20241008184109(原)
    # 20241008184109（漏清）
    # 20240907065212（漏清）\20240922140455\20240912182952
    # 20241008193945 20241008190221


    # 直接发送
    al_images_head_d = r"/home/hongtai/yolo/1002d/img/20241008190221/gray_img"
    al_images_head_u = r"/home/hongtai/yolo/depth_img/20241008190221/gray_img"#算法图片路径
    image_table_head_d = r'\\Grab2\192.168.100.2\\img\20241008190221\gray_img'
    image_table_head_u = r'\\Grab1\192.168.100.1\\img\20241008190221\gray_img'#图像缺陷路径
    caiji_2_al_head_d = r'D:\img\20241008190221\gray_img'
    caiji_2_al_head_u = r'D:\img\20241008190221\gray_img'   


    al_images_head_d = al_images_head_d.replace('20241008190221',main_id)
    al_images_head_u = al_images_head_u.replace('20241008190221',main_id)
    image_table_head_d=image_table_head_d.replace('20241008190221',main_id)
    image_table_head_u=image_table_head_u.replace('20241008190221',main_id)
    caiji_2_al_head_d =caiji_2_al_head_d.replace('20241008190221',main_id)
    caiji_2_al_head_u =caiji_2_al_head_u.replace('20241008190221',main_id)
    print(al_images_head_d)
    time.sleep(3)
    # 1_2430516611_1_one_1

    image_name_list_d = os.listdir(al_images_head_d)
    image_name_list_u = os.listdir(al_images_head_u)
    # 每秒发送一条消息
    while True:
        time.sleep(0.5)
        for img_name in image_name_list_d:
            print(img_name)
            try:
                match = extract_numbers_from_filename(img_name)
                cid = int(match[0])
                #flowid = int(match[2])
                flowid = ((int(match[2])-1)*3)+int(match[3])
            except:
                continue
            time.sleep(0.1)
            print("flowid",flowid)

            try:
                # 创建一个 TCP 套接字
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # 连接服务器
                client_socket.connect(server_address)
                
                image_table_path_d = image_table_head_d+"\\"+img_name
                caiji_2_al_path_d = caiji_2_al_head_d+"\\" +img_name
                gray_id = str(uuid.uuid4())
                rgb_id = str(uuid.uuid4())
                depth_id = str(uuid.uuid4())
                root_id = "567"
                surface_id = 3
                steel_length = int((flowid*0.17421*4096)/1000) 
                body_gray_d={ 
                    'id':gray_id,
                    'main_id':mainid,
                    'flow_id':flowid,
                    'image_url':image_table_path_d,
                    'type':2,
                    'surface_id':surface_id,
                    'camera_id':cid,
                    'insert_time':str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    'width':3072,
                    'height':4096,
                    'steel_length': steel_length,
                    "other0": "-41.329594",
                    "other1": "-41.329594"
                }
                body_depth_d={ 
                    'id':depth_id,
                    'main_id':mainid,
                    'flow_id':flowid,
                    'image_url':image_table_path_d.replace('gray_img','origin_img'),
                    'type':1,
                    'surface_id':surface_id,
                    'camera_id':cid,
                    'insert_time':str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    'width':3072,
                    'height':4096,
                    'steel_length': steel_length,
                    "other0": "-41.329594",
                    "other1": "-41.329594"
                }
                body_rgb_d={
                    'id':rgb_id,
                    'main_id':mainid,
                    'flow_id':flowid,
                    'image_url':image_table_path_d.replace('gray_img','rgb_img'),
                    'type':3,
                    'surface_id':surface_id,
                    'camera_id':cid,
                    'insert_time':str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    'width':3072,
                    'height':4096,
                    'steel_length':steel_length,
                    "other0": "-41.329594",
                    "other1": "-41.329594"
                }
                database.insert_image_es(body_gray_d)
                database.insert_image_es(body_depth_d)
                database.insert_image_es(body_rgb_d)
                message = construct_json_object(depth_id,gray_id,rgb_id,caiji_2_al_path_d,surface_id,cid,mainid,root_id, flowid,steel_length,cu_mainid_start_time,None)
                http_request = "POST / HTTP/1.1\r\n"
                http_request += "Host: 222.199.197.235:9002\r\n"
                http_request += "Content-Type: application/json\r\n"
                http_request += "Content-Length: {}\r\n".format(len(message))
                http_request += "\r\n"  # 请求头部结束
                http_request += message
                # print('http_request',http_request)
                client_socket.sendall(http_request.encode('utf-8'))
                # time.sleep(5)
                # 启动新线程接收回传信息
                recv_thread = threading.Thread(target=receive_message, args=(client_socket,))
                recv_thread.start()
            except Exception as e:
                print("An error occurred:", e)

            finally:
                # 关闭套接字
                if 'client_socket' in locals():
                    client_socket.close()
       


        for img_name in image_name_list_u:
            print(img_name)
            try:
                try:
                    match = extract_numbers_from_filename(img_name)
                    cid = int(match[0])
                    #flowid = int(match[2])
                    flowid = ((int(match[2])-1)*3)+int(match[3])
                    time.sleep(0.1)
                except:
                    continue
                print("flowid",flowid)
                # flowid = ((int(match[2])-1)*3)+int(match[4])
                time.sleep(0.1)
                # 创建一个 TCP 套接字
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # 连接服务器
                client_socket.connect(server_address)
                
                image_table_path_u = image_table_head_u+"\\"+img_name
                caiji_2_al_path_u = caiji_2_al_head_u+"\\" +img_name
                gray_id = str(uuid.uuid4())
                rgb_id = str(uuid.uuid4())
                depth_id = str(uuid.uuid4())
                root_id = "1234"
                if cid in [2,3]:
                    surface_id = 2
                elif cid == 1:
                    surface_id = 1
                elif cid == 4:
                    surface_id = 4
                steel_length = int((flowid*0.17421*4096)/1000) 
                body_gray_u={ 
                    'id':gray_id,
                    'main_id':mainid,
                    'flow_id':flowid,
                    'image_url':image_table_path_u,
                    'type':2,
                    'surface_id':surface_id,
                    'camera_id':cid,
                    'insert_time':str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    'width':3072,
                    'height':4096,
                    'steel_length': steel_length,
                    "other0": "-41.329594",
                    "other1": "-41.329594"
                }                
                body_depth_u={ 
                    'id':depth_id,
                    'main_id':mainid,
                    'flow_id':flowid,
                    'image_url':image_table_path_u.replace('gray_img','origin_img'),
                    'type':1,
                    'surface_id':surface_id,
                    'camera_id':cid,
                    'insert_time':str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    'width':3072,
                    'height':4096,
                    'steel_length': steel_length,
                    "other0": "-41.329594",
                    "other1": "-41.329594"
                }
                body_rgb_u={
                    'id':rgb_id,
                    'main_id':mainid,
                    'flow_id':flowid,
                    'image_url':image_table_path_u.replace('gray_img','rgb_img'),
                    'type':3,
                    'surface_id':surface_id,
                    'camera_id':cid,
                    'insert_time':str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                    'width':3072,
                    'height':4096,
                    'steel_length':steel_length,
                    "other0": "-41.329594",
                    "other1": "-41.329594"
                }
                database.insert_image_es(body_gray_u)                
                database.insert_image_es(body_depth_u)
                database.insert_image_es(body_rgb_u)
                message = construct_json_object(depth_id,gray_id,rgb_id,caiji_2_al_path_u,surface_id,cid,mainid,root_id, flowid,steel_length,cu_mainid_start_time,None)
                http_request = "POST / HTTP/1.1\r\n"
                http_request += "Host: 222.199.197.235:9002\r\n"
                http_request += "Content-Type: application/json\r\n"
                http_request += "Content-Length: {}\r\n".format(len(message))
                http_request += "\r\n"  # 请求头部结束
                http_request += message
                client_socket.sendall(http_request.encode('utf-8'))
                #启动新线程接收回传信息
                recv_thread = threading.Thread(target=receive_message, args=(client_socket,))
                recv_thread.start()
            except Exception as e:
                print("An error occurred:", e)
            finally:
                # 关闭套接字
                if 'client_socket' in locals():
                    client_socket.close()
        
        try:
            # 创建一个 TCP 套接字
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 连接服务器
            client_socket.connect(server_address)
            cu_mainid_end_time = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
            message = construct_json_object(0,0,0,0,0,0,mainid,0, 0,0,cu_mainid_start_time,cu_mainid_end_time,is_finish = True)
            http_request = "POST / HTTP/1.1\r\n"
            http_request += "Host: 222.199.197.235:9002\r\n"
            http_request += "Content-Type: application/json\r\n"
            http_request += "Content-Length: {}\r\n".format(len(message))
            http_request += "\r\n"  # 请求头部结束
            http_request += message
            
            client_socket.sendall(http_request.encode('utf-8'))
            print('发送结束') 
            a2c_message(mainid,cu_mainid_end_time,False)          
        except Exception as e:
            print("An error occurred:", e)
        finally:
            # 关闭套接字
            if 'client_socket' in locals():
                client_socket.close()
        break
        

def receive_message(client_socket):
    try:
        # 接收回传信息
        data = client_socket.recv(1024)
        print("Received:", data.decode('utf-8'))
    except Exception as e:
        print("An error occurred while receiving:", e)
    finally:
        # 关闭套接字
        client_socket.close()

def a2c_message(main_id,time,is_start):
    
    s_path = 'http://192.168.100.100:8094/steelinfo'
    e_path = 'http://192.168.100.100:8094/steelfinish'
    if is_start:
        s_data = {
                'user_custom_id':main_id,
                'insert_time': str(time),                    
                'main_id':main_id,
                'sd':24,
                'real_length':5739.5695,
                'real_width':1924,
                'real_height':224,
            }
        header_info = {
            "Content-type": "application/json;charset=utf-8"
        }
        proxies={
            'http': 'http://192.168.100.100:8094'
        }
        res = requests.post(url=s_path, data=json.dumps(s_data, ensure_ascii=False).encode('utf-8'),proxies=proxies,headers=header_info,timeout=5) 
        print('起始：',res)
    else:
        e_data = {
                'end_time':str(time)
            }
        header_info = {
            "Content-type": "application/json;charset=utf-8"
        }
        proxies={
            'http': 'http://192.168.100.100:8094'
        }
        res = requests.post(url=e_path, data=json.dumps(e_data, ensure_ascii=False).encode('utf-8'),proxies=proxies, headers=header_info,timeout=5) 
        print('结束：',res)
if __name__ == "__main__":
    sys_setting = MySettings()
    database = MyDatabase(sys_setting)
    database.create_es()
    ids = []
    # for id in ids:
    #     send_message(id)
    # 20241007171309/
    send_message('20241005145532')
    
