import os
import cv2
def get_small_images(image, json_dict, width_boundary=4096, crop_width=640,crop_height=640):  # 考虑加纵方向偏移
        left = json_dict['left_edge']
        right = json_dict['right_edge']

        # 存储非全黑图像块的列表
        non_black_block = []
        # 存储非全黑图像块左上角相对大图的位置（offset_x,offset_y）
        non_black_offset = []
        
        if 0 <= left <= width_boundary and 0 <= right <= width_boundary:
            current_left = left
            current_up = 0
            pic_num_x = (int(right) - int(left)) // crop_width
            yushu_x = (int(right) - int(left)) % crop_width
            print(pic_num_x,yushu_x)
            pic_num_y = 3
            yushu_y = 128
            # 太短的不分析了
            if right-left<100:
                return ([json_dict] * len(non_black_block), non_black_offset, non_black_block)
            # 处理640倍数的图像x
            for _ in range(pic_num_x):
                for _ in range(pic_num_y):
                    temp_img = image[current_up:current_up+crop_height, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left,current_up))
                    current_up+=crop_height
                if yushu_y>100 and pic_num_y>0:
                    end_edge = current_up+yushu_y-1
                    temp_img = image[end_edge-crop_height:end_edge, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left,end_edge-crop_height))

                current_left += crop_width
                current_up = 0
            # 处理不足640的x方向的内容:边部相机可能right_left不够640或者存在一个裁剪之后剩下一个余数
            
            if current_left + crop_width < width_boundary :#对于最右相机不足640
                current_left = left
            elif right - crop_width > 0:#对于最左相机不足640
                current_left = right-crop_width
            else:
                current_left = None
            if current_left is not None:
                for _ in range(pic_num_y):
                    temp_img = image[current_up:current_up+crop_height, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left,current_up))
                    current_up+=crop_height
                if yushu_y>100 and pic_num_y>0:
                    end_edge = current_up+yushu_y-1
                    temp_img = image[end_edge-crop_height:end_edge, current_left:current_left + crop_width]
                    non_black_block.append(temp_img)
                    non_black_offset.append((current_left,end_edge-crop_height))

        else:
            return (None, non_black_offset, None)
        return (None, non_black_offset, None)
if __name__ == "__main__":
    pic = cv2.imread('/home/deployer/NNL/Test/00000_1.jpg')
    json_dic = {'left_edge':3200,'right_edge':4095}
    print(get_small_images(pic,json_dic))
