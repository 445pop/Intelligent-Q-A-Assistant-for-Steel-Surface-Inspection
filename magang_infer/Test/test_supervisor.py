import os
from datetime import datetime
import time
'''
测试自启动
'''
def write_to_file():
    filename = "example.txt"
    content = f"Current time: {datetime.now()}"

    if os.path.exists(filename):
        with open(filename, "a") as file:
            file.write("\n" + content)
    else:
        with open(filename, "w") as file:
            file.write(content)
    print('hello')
    while True:
        time.sleep(1)

if __name__ == "__main__":
    write_to_file()
