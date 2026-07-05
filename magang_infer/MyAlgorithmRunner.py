import argparse
import multiprocessing
import time
import atexit
import sys
import signal

from MyObject.MyMethod import DatabaseProcess, InferProcess, PeriodicCheckProcess, HttpProcess
from MyObject.ProjectConfig import MySettings


#  setup_terminate_process(self): 这个函数主要用于设置进程终止的信号处理，清除缓存具体步骤如下：

#  定义了一个名为 handle_exit 的函数，用于处理程序的退出。当接收到 SIGTERM 或 SIGINT 信号时，此函数会将 self.alive.value 设置为 False，表示进程不再存活，然后调用 sys.exit() 退出程序。
#  使用 atexit.register(handle_exit) 将 handle_exit 函数注册到 atexit 模块中，以确保在程序正常退出时也能执行相应的退出操作。
#  使用 signal.signal(signal.SIGTERM, handle_exit) 和 signal.signal(signal.SIGINT, handle_exit) 分别将 handle_exit 函数注册为 SIGTERM 和 SIGINT 信号的处理函数，以便在接收到这些信号时执行相同的退出操作。

# def setup_terminate_process(logger,alive):
#     def handle_exit(signum=None, frame=None):
#         alive.value = False
#         logger.info('已执行后处理')
#         sys.exit()

#     atexit.register(handle_exit)
#     signal.signal(signal.SIGTERM, handle_exit)
#     signal.signal(signal.SIGINT, handle_exit)

def main():
    # 多进程共享类对象
    manager = multiprocessing.Manager()
    # 创建配置文件对象
    sys_setting = MySettings()
    cfg_runner = sys_setting.cfg_runner
    # http接收图像信息队列 送入InferProcess 推理
    json_queue = multiprocessing.Queue()
    # 数据库变化信息队列 送入DatabaseProcess 数据库
    res_queue = multiprocessing.Queue()
    # 完成批次推理的批次号队列 需送入PeriodicCheckProcess总结
    finished_queue = multiprocessing.Queue()
    alive = multiprocessing.Value('b', True)
    # 20240534 添加共享变量alarmCancelled免打扰模式/取消报警
    alarmCancelled = multiprocessing.Value('b', False)
    # 推理进程全局共享变量
    steels_dic = manager.dict()
    # 推理进程与数据库进程 的全局共享变量 存储已发送summary的批次号，避免重复summary
    finished_mainid_list = manager.list()
    # 接收http请求的进程：采集+软件
    infer_list = []
    h = HttpProcess(0, alive, alarmCancelled, json_queue, finished_queue, sys_setting)
    h.start()

    sys_setting.logger.error("----------------------等待100s，初始化华为卡-------------------------")
    time.sleep(1)
    sys_setting.logger.error("----------------------准备开始初始化推理进程-------------------------")
    for index in range(cfg_runner['Detect']['process_num']):
        # process_num为推理进程数，可以在setting配置文件中修改
        i = InferProcess(index, alive, alarmCancelled, json_queue, res_queue, steels_dic
                         , sys_setting)
        i.start()
        infer_list.append(i)
    # 数据库进程
    d = DatabaseProcess(0, alive, res_queue, finished_queue, finished_mainid_list, sys_setting)
    d.start()
    # 历史原因 名称实际含义是总结已推理结束的批次 拿到钢材缺陷、报警等等
    p = PeriodicCheckProcess(0, alive, alarmCancelled, finished_queue, sys_setting)
    p.start()

    def handle_exit(signum=None, frame=None):
        alive.value = False
        sys.exit()

    atexit.register(handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    while alive.value == True:
        time.sleep(60)
        # alive.value = False


if __name__ == '__main__':
    main()
