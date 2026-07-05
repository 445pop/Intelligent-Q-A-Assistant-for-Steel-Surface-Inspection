from PIL import Image
import os

# 图像文件路径
img_path = "/diskb/server101/3/2024_04_20_17_19_57/X52404258002-014/data_8815.png"

# 打开图像文件
try:
    with Image.open(img_path) as img:
        # 获取图像内容
        img_data = img.getdata()
        print("Image loaded successfully.")
except Exception as e:
    print(f"Failed to load image: {img_path}")
    print(f"Error message: {e}")
