import cv2
import time

url = '' #RTSP URL
cap = cv2.VideoCapture(url)

# 저장할 비디오 설정
fps = 15  # 프레임 수 (초당 몇 장)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # mp4로 저장
out = cv2.VideoWriter('output_30s.mp4', fourcc, fps, (width, height))

print("녹화 시작")

start_time = time.time()
while time.time() - start_time < 30:  # 30초 동안
    ret, frame = cap.read()
    if not ret:
        print("카메라에서 프레임을 읽지 못했습니다.")
        break
    out.write(frame)  # 프레임 저장
    cv2.imshow("Recording", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):  # q 누르면 종료
        break

cap.release()
out.release()
cv2.destroyAllWindows()

print("30초 영상 저장 완료: output_30s.mp4")