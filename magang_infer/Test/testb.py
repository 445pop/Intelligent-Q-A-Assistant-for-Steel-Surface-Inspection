import os  
import re  
import shutil
def is_valid_timestamp(filename):  
    """  
    检查文件名是否符合YYYYMMDDHHMMSS格式  
    """  
    pattern = r'^\d{14}$'  # 匹配14位数字  
    return bool(re.match(pattern, filename))  
  
def delete_invalid_files(directory):  
    """  
    删除指定目录下不符合YYYYMMDDHHMMSS格式的文件  
    """  
    for filename in os.listdir(directory):  
        if not is_valid_timestamp(filename):  
            file_path = os.path.join(directory, filename)  
            try:  
                #shutil.rmtree(file_path)
                os.remove(file_path)  
                print(f"Deleted: {file_path}")  
            except OSError as e:  
                print(f"Error: {e.strerror} on {file_path}")  
  
# 指定要清理的文件夹路径  
directory_path = '/home/hongtai/yolo/depth_img'
  
# 调用函数  
delete_invalid_files(directory_path)