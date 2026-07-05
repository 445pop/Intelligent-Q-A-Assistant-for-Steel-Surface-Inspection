# -*- coding: utf-8 -*-
"""
Created on Wed Aug 29 13:33:20 2018
@author: Li Zeng hai
"""
import os
import shutil
import time
from distutils.core import setup
from Cython.Build import cythonize

file_path_list = ["data_collect.py", "deployUtils.py", "StitchUtil.py", "Stitcher.py"]
file_path_util_list = ["auth.py", "rsa_encryption_for_auth.py", "RSA_KEY_for_auth.py"]
# for i in range(0, len(file_path_list)):
# os.popen('python build_pyd.py build_ext --inplace')
# 在file_path填写需要转换的文件名
file_path = file_path_list[1]

# auth.py
# rsa_encryption_for_auth.py
# RSA_KEY_for_auth.py
# ImageFusion.py
# ImageUtility.py
# StitchUtil.py
# Stitcher.py

setup(
    name='any words.....',
    ext_modules=cythonize(file_path, compiler_directives={'language_level': 3})
)
time.sleep(2)
# 删除生成的c语言文件
filename = file_path.split('.py')[0]
os.remove('%s.c' % filename)
# if i < 3:
#     # 删除生成的build文件夹
#     build_folder_path = os.path.join(os.getcwd(), 'util', 'build')
#     shutil.rmtree(build_folder_path)
# else:
# 删除生成的build文件夹
build_folder_path = os.path.join(os.getcwd(), 'build')
shutil.rmtree(build_folder_path)

