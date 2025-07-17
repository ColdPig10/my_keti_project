import os
import json
import requests
import cv2
from towhee import pipe, ops

# 이미지 임베딩을 위한 파이프라인 정의
p_embed = (
    pipe.input('img_path')
    .map('img_path', 'img', ops.image_decode())
    .map('img', 'vec', ops.image_embedding.timm(model_name='resnet50', device=None))
    .output('img_path', 'vec')
)

# HTTP 전송을 위한 설정
milvusServerURL = ''
headers = {'Content-type': 'application/json', 'Accept': 'text/json'}

def embed_and_send_car_image(car_img_path):
    try:
        result = p_embed(car_img_path).to_list()
        if result:
            img_path, vec = result[0]
            # numpy 배열을 리스트로 변환
            vec_list = vec.tolist()
            embedding_payload = json.dumps({'img_path': img_path, 'embedding': vec_list})
            embedding_response = requests.post(milvusServerURL, headers=headers, data=embedding_payload)
            print("Embedding POST request status code:", embedding_response.status_code)
            print("Embedding POST request text:", embedding_response.text)
    except Exception as e:
        print(f"Error embedding and sending car image: {e}")

# Dummy values for demonstration
car_img_path = 'C:/Users/CoTLab/Downloads/detection/test_car.jpg'

embed_and_send_car_image(car_img_path)
