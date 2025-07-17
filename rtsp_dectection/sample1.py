# import torch
# from torchvision import transforms
# from PIL import Image
# import requests
# import matplotlib.pyplot as plt
# import cv2
# import numpy as np

# # DETR 모델과 가중치 불러오기
# model = torch.hub.load('facebookresearch/detr', 'detr_resnet50', pretrained=True)
# model.eval()

# # 박스 스케일링 함수
# def rescale_bboxes(out_bbox, size):
#     img_w, img_h = size
#     b = box_cxcywh_to_xyxy(out_bbox)
#     b = b * torch.tensor([img_w, img_h, img_w, img_h], dtype=torch.float32)
#     return b

# def box_cxcywh_to_xyxy(x):
#     x_c, y_c, w, h = x.unbind(1)
#     b = [(x_c - 0.5 * w), (y_c - 0.5 * h),
#          (x_c + 0.5 * w), (y_c + 0.5 * h)]
#     return torch.stack(b, dim=1)


# # 변환 정의
# transform = transforms.Compose([
#     transforms.Resize(800),
#     transforms.ToTensor(),
#     transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
# ])

# file_name = 'sample.mov'

# cap = cv2.VideoCapture(file_name)

# if cap.isOpened():
#     while True:
#         ret,image = cap.read()
#         if ret:
#             # 이미지 변환 적용
#             img = image

#             # 모델 예측
#             with torch.no_grad():
#                 outputs = model(img)

#             # 출력에서 박스와 라벨 추출
#             probas = outputs['pred_logits'].softmax(-1)[0, :, :-1]
#             keep = probas.max(-1).values > 0.7

#             bboxes_scaled = rescale_bboxes(outputs['pred_boxes'][0, keep], image.size)


#             ### 2. 이미지에 사각형 그리기

#             # 이미지 읽기 (OpenCV)
#             image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

#             # 박스 그리기
#             for box in bboxes_scaled:
#                 x_min, y_min, x_max, y_max = box.int().numpy()
#                 cv2.rectangle(image_cv, (x_min, y_min), (x_max, y_max), color=(0, 255, 0), thickness=2)

#             # 결과 이미지 보여주기 (matplotlib)
#             cv2.imshow(image_cv, image_cv)
import torch
from torchvision import transforms
from PIL import Image
import requests
import matplotlib.pyplot as plt
import cv2
import numpy as np

# DETR 모델 불러오기
model = torch.hub.load('facebookresearch/detr', 'detr_resnet50', pretrained=True)
model.eval()

# 박스 변환 함수
def box_cxcywh_to_xyxy(x):
    x_c, y_c, w, h = x.unbind(1)
    b = [(x_c - 0.5 * w), (y_c - 0.5 * h),
         (x_c + 0.5 * w), (y_c + 0.5 * h)]
    return torch.stack(b, dim=1)

def rescale_bboxes(out_bbox, size):
    img_w, img_h = size
    b = box_cxcywh_to_xyxy(out_bbox)
    b = b * torch.tensor([img_w, img_h, img_w, img_h], dtype=torch.float32)
    return b

# 이미지 전처리
transform = transforms.Compose([
    transforms.Resize(800),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

file_name = 'sample.mov'
cap = cv2.VideoCapture(file_name)

if cap.isOpened():
    while True:
        ret, image = cap.read()
        if not ret:
            break

        # OpenCV → PIL 변환
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        # Transform 적용
        img_tensor = transform(pil_image).unsqueeze(0)  # [1, 3, H, W]

        # 모델 추론
        with torch.no_grad():
            outputs = model(img_tensor)

        # 확률 및 박스 추출
        probas = outputs['pred_logits'].softmax(-1)[0, :, :-1]
        keep = probas.max(-1).values > 0.7

        bboxes_scaled = rescale_bboxes(outputs['pred_boxes'][0, keep], pil_image.size)

        # 박스 그리기 (원본 이미지 기준)
        for box in bboxes_scaled:
            x_min, y_min, x_max, y_max = box.int().numpy()
            cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

        # 결과 출력
        cv2.imshow('DETR Object Detection', image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
