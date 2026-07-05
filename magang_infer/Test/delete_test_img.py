import os  
from datetime import datetime, timedelta  
  
def folder_name_to_datetime(folder_name):  
    """  
    尝试将形如'20240620062832'的文件夹名转换为datetime对象。  
      
    :param folder_name: 文件夹名  
    :return: datetime对象或None（如果转换失败）  
    """  
    try:  
        return datetime.strptime(folder_name[:8], '%Y%m%d')  # 只取前8位作为日期  
    except ValueError:  
        return None  
  
def delete_old_folders(directory, threshold_days=30):  
    """  
    删除指定目录内命名表示的时间超过指定天数的文件夹。  
      
    :param directory: 要搜索的目录路径  
    :param threshold_days: 超过这个天数的文件夹将被删除  
    """  
    now = datetime.now()  
    threshold = now - timedelta(days=threshold_days)  
      
    for folder_name in os.listdir(directory):  
        folder_path = os.path.join(directory, folder_name)  
        # 注意：这里我们实际上没有检查文件夹的最后修改时间，而是基于文件夹名  
        folder_datetime = folder_name_to_datetime(folder_name)  
        if folder_datetime and folder_datetime < threshold:  
            # 确保这是一个文件夹而不是文件  
            if os.path.isdir(folder_path):  
                try:  
                    import shutil  
                    shutil.rmtree(folder_path)  
                    print(f"Deleted folder: {folder_path}")  
                except Exception as e:  
                    print(f"Failed to delete folder {folder_path}: {e}")  
  
# 使用示例  
if __name__ == "__main__":  
    TARGET_DIR = "/home/hongtai/yolo/1002d/test_img"  # 设置你的目标目录  
    delete_old_folders(TARGET_DIR)