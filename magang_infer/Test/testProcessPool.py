import multiprocessing

# 定义一个 CPU 密集型函数，这里使用一个简单的计算斐波那契数列的例子
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    # 创建进程池，指定最大进程数为 CPU 核心数
    pool = multiprocessing.Pool(processes=2)

    # 定义任务列表，这里假设要计算前 10 个斐波那契数
    tasks = [10, 20, 30,35]

    # 使用进程池并行执行任务
    results = pool.map(fibonacci, tasks)

    # 关闭进程池，等待所有进程结束
    pool.close()
    pool.join()

    # 输出结果
    for i, result in enumerate(results):
        print(f"Fibonacci({tasks[i]}) = {result}")
