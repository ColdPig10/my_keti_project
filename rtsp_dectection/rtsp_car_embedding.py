import os
import requests
import cv2
import torch
import json
import ast
from towhee import pipe, ops
from transformers import DetrImageProcessor, DetrForObjectDetection
from PIL import Image

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(device)

# 전역 변수 설정
save_mode = False
rectangles = []

def is_point_in_rectangle(x, y, rect):
    x_min, y_min, x_max, y_max = rect
    # 점이 사각형의 범위 안에 있는지 확인
    return x_min <= x <= x_max and y_min <= y <= y_max

# 절대 경로 설정
base_dir = 'C:/Users/CoTLab/Downloads/detection'
tmp_dir = os.path.join(base_dir, 'tmp')
result_dir = os.path.join(base_dir, 'results')

# tmp 및 results 디렉토리 생성
if not os.path.exists(tmp_dir):
    os.makedirs(tmp_dir)
if not os.path.exists(result_dir):
    os.makedirs(result_dir)

url = '' #RTSP URL

# 이미지 임베딩을 위한 파이프라인 정의
p_embed = (
    pipe.input('img_path')
    .map('img_path', 'img', ops.image_decode())
    .map('img', 'vec', ops.image_embedding.timm(model_name='resnet50', device=None))
    .output('img_path', 'vec')
)

# HTTP 전송을 위한 설정
headers = {'Content-type': 'application/json', 'Accept': 'text/json'}
milvusServerURL = ''

def main():
    try:
        if save_mode:
            cap = cv2.VideoCapture(url)
            ret, img = cap.read()
            if ret:
                cv2.imshow('Save Mode', img)
                key = cv2.waitKey(0) & 0xFF
                if key == ord('s'):
                    with open(os.path.join(base_dir, 'grid.txt'), 'w') as f:
                        f.write(str(rectangles))
            cv2.waitKey(5)
        else:
            with open(os.path.join(base_dir, 'grid.txt'), 'r') as f:
                data = ast.literal_eval(f.read())
                print(f"Loaded {len(data)} rectangles.")

            processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-101", revision="no_timm")
            model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-101", revision="no_timm")
            model.to(device)
            cap = cv2.VideoCapture(url)
            color = (255, 0, 0)  # 파란색
            thickness = 2  # 두께
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            font_color = (255, 255, 255)  # 흰색
            font_thickness = 2
            label_set = ['car']

            if cap.isOpened():
                while True:
                    ret, img = cap.read()
                    if ret:
                        inputs = processor(images=img, return_tensors="pt").to(device)
                        outputs = model(**inputs)
                        target_sizes = torch.tensor([img.shape[:2]])
                        results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.3)[0]
                        send = {}
                        n = 0
                        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                            tmp_label = model.config.id2label[label.item()]
                            if tmp_label in label_set:
                                n += 1
                                box = [round(i, 2) for i in box.tolist()]
                                mid_point = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                                for ind, rec in enumerate(data):
                                    if is_point_in_rectangle(mid_point[0], mid_point[1], rec):
                                        cropped_img = img[int(box[1]):int(box[3]), int(box[0]):int(box[2])]
                                        car_img_path = os.path.join(tmp_dir, f'car_{ind}_{n}.jpg')
                                        cv2.imwrite(car_img_path, cropped_img)
                                        try:
                                            result = p_embed(car_img_path).to_list()
                                            if result:
                                                img_path, vec = result[0]
                                                vec_list = vec.tolist()
                                                embedding_payload = json.dumps({'img_path': img_path, 'embedding': vec_list})
                                                embedding_response = requests.post(milvusServerURL, headers=headers, data=embedding_payload)
                                                print("Embedding POST request status code:", embedding_response.status_code)
                                                print("Embedding POST request text:", embedding_response.text)
                                                
                                                # search_result 값 추출
                                                response_data = json.loads(embedding_response.text)
                                                search_result = response_data.get('search_result', 'unknown')
                                                
                                                # 이미지 결과 경로에 search_result 추가
                                                car_img_result_path = os.path.join(result_dir, f'car_{ind}_{n}_{search_result}.jpg')
                                                cv2.imwrite(car_img_result_path, cropped_img)
                                                print("Image saved at: ", car_img_result_path)
                                                print("\n")
                                        except Exception as e:
                                            print(f"Error embedding and sending car image: {e}")
                        cv2.waitKey(5)
    except Exception as e:
        print('Error occurred:', e)

if __name__ == "__main__":
    main()
