import socket
import json
import threading
import time
import uuid  
from datetime import datetime

def construct_json_object(cu_mainid_start_time,cur_main_id, flow_id,is_finish = None ):  
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
      
     
    
    camera_id = 1
    # 构造Python字典，模拟C++中的JSON对象  
    if is_finish is None:
        suanfa = {  
            "id": str(uuid.uuid4()),  # 使用Python的uuid库生成UUID  
            "main_id": cur_main_id,  
            "flow_id": flow_id,  
            "image_url": "/home/deployer/NNL/Test/00000_1.jpg" , 
            "type": 1,  
            "surface_id": camera_id,  
            "camera_id": camera_id,  
            "insert_time": str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))  ,  
            "has_steel": True,  
            "root_id":"112",
            "left": 1000,
            "has_top": False,  
            "has_bottom": False,  
            "width": 4096,  
            "height": 2048,  
            "is_delete": False,  
            "steel_length": flow_id * 0.0368,  
            "left_edge": 1000,  
            "right_edge": 1650,  
            "signal": 0  
        }  
    else:
        
        suanfa = {"end_time":str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),"insert_time":cu_mainid_start_time,"main_id":cur_main_id,"signal":1}
    # 将Python字典转换为JSON字符串  
    json_str = json.dumps(suanfa, ensure_ascii=False, indent=4)  
      
    # 返回JSON字符串  
    return json_str 

def send_message():
    # 服务器地址和端口
    server_address = ('192.168.2.111', 9000)
    flow_id = 0
    cu_mainid_start_time = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    mainid = datetime.now().strftime("%Y%m%d%H%M%S") 
    # 每秒发送一条消息
    while True:
        try:

            # 创建一个 TCP 套接字
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 连接服务器
            client_socket.connect(server_address)

            
            if flow_id<30:
                # 发送消息
                message = construct_json_object(cu_mainid_start_time,str(mainid),flow_id)
            else:
                message = construct_json_object(cu_mainid_start_time,str(mainid),flow_id,True)

            
            http_request = "POST / HTTP/1.1\r\n"
            http_request += "Host: 222.199.197.235:9002\r\n"
            http_request += "Content-Type: application/json\r\n"
            http_request += "Content-Length: {}\r\n".format(len(message))
            http_request += "\r\n"  # 请求头部结束
            http_request += message
            # sender_socket.sendall(message.encode())
            client_socket.sendall(http_request.encode('utf-8'))
            print('send ',http_request)

            # 启动新线程接收回传信息
            recv_thread = threading.Thread(target=receive_message, args=(client_socket,))
            recv_thread.start()

        except Exception as e:
            print("An error occurred:", e)

        finally:
            # 关闭套接字
            if 'client_socket' in locals():
                client_socket.close()
        
        # 暂停1秒
        flow_id+=1
        time.sleep(0.3)

        if flow_id>10:
            flow_id = 0
            time.sleep(60)
            mainid = datetime.now().strftime("%Y%m%d%H%M%S") 
            cu_mainid_start_time = str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

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


if __name__ == "__main__":
    send_message()
    
