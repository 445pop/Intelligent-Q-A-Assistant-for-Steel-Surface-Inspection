import socket
import json

# 服务器地址和端口
SERVER_ADDRESS = ('localhost', 9003)

def main():
    # 创建一个 TCP 套接字
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(SERVER_ADDRESS)
    server_socket.listen(5)

    print("Server is listening at", SERVER_ADDRESS)

    while True:
        # 接受客户端连接
        client_socket, client_address = server_socket.accept()
        print("Connected to", client_address)

        # 接收客户端发送的数据
        data = client_socket.recv(1024)
        if data:
            message = data.decode('utf-8')
            print("Received:", message)

            # 回传消息
            response_message = {"response": "Received message successfully"}
            response_json = json.dumps(response_message)
            client_socket.sendall(response_json.encode('utf-8'))

        # 关闭连接
        client_socket.close()

if __name__ == "__main__":
    main()
