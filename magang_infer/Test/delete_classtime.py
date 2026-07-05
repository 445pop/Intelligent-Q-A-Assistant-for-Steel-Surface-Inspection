import os  
import re  
import shutil 
 
from datetime import datetime, timedelta  
  
def is_valid_and_not_old(filename, cutoff_date):  
    """  
    检查文件名是否符合YYYYMMDDHHMMSS格式，并且日期不早于cutoff_date  
    """  
    try:  
        # 尝试从文件名中提取日期并转换为datetime对象  
        file_date_str = filename[:14]  # 假设文件名前14位是日期时间  
        file_date = datetime.strptime(file_date_str, "%Y%m%d%H%M%S")  
        # 检查日期是否不早于cutoff_date  
        return file_date >= cutoff_date  
    except ValueError:  
        # 如果文件名不是有效的日期时间格式，则返回False  
        return False  
  
def delete_invalid_and_old_files(directory, cutoff_year, cutoff_month, cutoff_day):  
    """  
    删除指定目录下不符合YYYYMMDDHHMMSS格式或日期早于指定日期的文件  
    """  
    cutoff_date = datetime(cutoff_year, cutoff_month, cutoff_day)  
    for filename in os.listdir(directory):  
        if not is_valid_and_not_old(filename, cutoff_date):  
            file_path = os.path.join(directory, filename)  
            try:  
                shutil.rmtree(file_path)  
                print(f"Deleted: {file_path}")  
            except OSError as e:  
                print(f"Error deleting {file_path}: {e.strerror}")  
  
# 指定要清理的文件夹路径和截止日期  
directory_path = '/home/hongtai/yolo/1002d/img'
cutoff_year = 2024  
cutoff_month = 6  
cutoff_day = 30 
  
# 调用函数  
delete_invalid_and_old_files(directory_path, cutoff_year, cutoff_month, cutoff_day)
# def is_valid_timestamp(filename):  
#     """  
#     检查文件名是否符合YYYYMMDDHHMMSS格式  
#     """  
#     pattern = r'^\d{14}$'  # 匹配14位数字  
#     return bool(re.match(pattern, filename))  
  
# def delete_invalid_files(directory):  
#     """  
#     删除指定目录下不符合YYYYMMDDHHMMSS格式的文件  
#     """  
#     for filename in os.listdir(directory):  
#         if not is_valid_timestamp(filename):  
#             file_path = os.path.join(directory, filename)  
#             try:  
#                 #os.remove(file_path)
#                 shutil.rmtree(file_path)  
#                 print(f"Deleted: {file_path}")  
#             except OSError as e:  
#                 print(f"Error: {e.strerror} on {file_path}")  
  
# # 指定要清理的文件夹路径  
# directory_path ='/home/hongtai/yolo/1002d/test_img'
  
# # 调用函数  
# delete_invalid_files(directory_path)