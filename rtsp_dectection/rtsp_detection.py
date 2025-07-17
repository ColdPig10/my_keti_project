#rtsp_detection.py

from transformers import DetrImageProcessor, DetrForObjectDetection
import torch
from PIL import Image
import requests
import cv2
import copy
import json
import ast

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(device)

# 전역 변수 설정
save_mode = False
drawing = False  # 마우스 드래그 상태 확인용
rectangle_on = True
ix, iy = -1, -1
rectangles = []  

def is_point_in_rectangle(x, y, rect):
    x_min, y_min, x_max, y_max = rect

    # 점이 사각형의 범위 안에 있는지 확인
    if x_min <= x <= x_max and y_min <= y <= y_max:
        return True
    else:
        return False

# 마우스 이벤트 콜백 함수
def draw_rectangle(event, x, y, flags, param):
    global ix, iy, drawing, rectangles
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            cv2.rectangle(img, (ix, iy), (x, y), (0, 255, 0), 1)
            cv2.imshow('zone mode', img)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.rectangle(img, (ix, iy), (x, y), (0, 255, 0), 1)
        rectangles.append((ix, iy, x, y))
        print(rectangles)
        # 사각형에 해당하는 이미지를 잘라내어 리스트에 추가


url = ''

#cv2.namedWindow('zone mode')
#cv2.setMouseCallback('zone mode', draw_rectangle)

# you can specify the revision tag if you don't want the timm dependency
while True:
    try:
        if save_mode == True:
            cap = cv2.VideoCapture(url)
            ret,img = cap.read()
            #cv2.imshow('zone mode', img)
            key = cv2.waitKey(0) & 0xFF 
            if key == ord('s'):
                f = open('grid.txt','w')
                f.write(str(rectangles)) 
                f.close()    
            cv2.waitKey(5)

        elif save_mode == False:
            f = open('grid.txt','r')
            data = f.read()
            data = ast.literal_eval(data)
            print(len(data))
            f.close()
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
            label_set = ['person','car']
            mirrorlakeURL = 'h'
            headers = {'Content-type': 'application/json', 'Accept':'text/json'}
            if cap.isOpened():
                while True:
                    cap = cv2.VideoCapture(url)
                    ret,img = cap.read()
                    #print('hihihi',img.shape)
                    if ret:
                        
                        inputs = processor(images=img, return_tensors="pt").to(device)
                        
                        outputs = model(**inputs)
                        
                        target_sizes = torch.tensor([img.shape[:2]])
                        results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.3)[0]
                        send = {}
                        n=0
                        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                            tmp_label = model.config.id2label[label.item()]
                            if tmp_label in label_set:
                                n+=1
                                box = [round(i, 2) for i in box.tolist()]
                                start_point1 = (int(box[0]),int(box[1]))  # 왼쪽 위 좌표 (x, y)
                                end_point1 = (int(box[2]),int(box[3]))
                                mid_point = ((box[0]+box[2])/2,(box[1]+box[3])/2)
                                index = 9999
                                for ind,rec in enumerate(data):
                                    box_in = is_point_in_rectangle(mid_point[0],mid_point[1],rec)
                                    if box_in == True:
                                        cv2.rectangle(img,(rec[0],rec[1]),(rec[2],rec[3]),(0,255,0),2)
                                        index=ind
                                        break
                                #print('here', start_point1, end_point1)
                                cv2.rectangle(img, start_point1, end_point1, color, thickness)
                                label_position1 = (start_point1[0], start_point1[1] - 10)
                                cv2.putText(img, str(model.config.id2label[label.item()]), label_position1, font, font_scale, font_color, font_thickness, cv2.LINE_AA)
                                print(
                                        f"Detected {model.config.id2label[label.item()]} with confidence "
                                        f"{round(score.item(), 3)} at location {box}"
                                )
                                tmp_input = {'box_data':box,'label_data':tmp_label,'score':round(score.item(), 3),'mid_point':mid_point,'grid_index':index}
                                send['object'+str(n)]=tmp_input
                        payload = json.dumps({'data':send})
                        response = requests.request("post", mirrorlakeURL, headers=headers, data=payload)
                        print("POST request status code:", response.status_code)
                        print("POST request text:", response.text)
                        print('\n')
                        #response = requests.post(mirrorlakeURL, headers=headers, data=payload)
                        cv2.imshow('video', img)
                        cv2.waitKey(5)
    except Exception as e:    # 모든 예외의 에러 메시지를 출력할 때는 Exception을 사용
        print('error occur : ', e)
