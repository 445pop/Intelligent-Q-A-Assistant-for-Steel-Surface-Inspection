from pprint import pprint
import onnxruntime

#onnx_path = "/home/hongtai/workspace/XX_infer_project/yolov8/infer_atalas/ultralytics/v8_add_head.onnx"
onnx_path = "/home/hongtai/yolo/magang_infer/SteelDefectDetection-magang/magang_infer/yolov8/infer_atalas/ultralytics/mg_all_20240630.onnx"

# onnx_path = "custompool/output.onnx"

provider = "CPUExecutionProvider"
onnx_session = onnxruntime.InferenceSession(onnx_path, providers=[provider])

print("----------------- ")
input_tensors = onnx_session.get_inputs() 
for input_tensor in input_tensors:        
    
    input_info = {
        "name" : input_tensor.name,
        "type" : input_tensor.type,
        "shape": input_tensor.shape,
    }
    pprint(input_info)

print("---------------------")
output_tensors = onnx_session.get_outputs()  
for output_tensor in output_tensors:        
    
    output_info = {
        "name" : output_tensor.name,
        "type" : output_tensor.type,
        "shape": output_tensor.shape,
    }
    pprint(output_info)
