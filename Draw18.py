import cv2
import numpy as np
import serial
import time

# ---------------- Setup ------------------------------------------------------------------------------------------------------
IMAGE_PATH = "NearnumJahanium.jpg"       # Input images
#IMAGE_PATH = "scotty.png"
#IMAGE_PATH = "drawing.png"
APPROX_EPSILON = 0.0001                  # Contour approximation accuracy (fraction of arc length)
SERIAL_PORT = "COM3"                     # Arduino COM port
BAUD = 115200
PEN_UP = "PEN_UP\n"
PEN_DOWN = "PEN_DOWN\n"
MOVE_CMD = "MOVE {:.2f} {:.2f}\n"
ANCHOR_WIDTH_MM = 1753                    # distance between top corners
MAX_Y_MM = 1219                           # max drop of robot


# --- Load & Threshold Image -------------------------------------------------------------------------------------------------
img = cv2.imread(IMAGE_PATH, cv2.IMREAD_GRAYSCALE)
h, w = img.shape
binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 9, 10)

#--- Extract Contours --------------------------------------------------------------------------------------------------------
contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

#--- Vectorization -----------------------------------------------------------------------------------------------------------
vector_paths = []

for contour in contours:
    epsilon = APPROX_EPSILON * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    approx = approx.reshape(-1, 2)
    vector_paths.append(approx)

#--- Scaling image -----------------------------------------------------------------------------------------------------------
SCALE_X = ANCHOR_WIDTH_MM / w
SCALE_Y = MAX_Y_MM / h
SCALE = min(SCALE_X, SCALE_Y)

def to_mm(pt):
    return pt[0] * SCALE, pt[1] * SCALE

#--- Ordering ----------------------------------------------------------------------------------------------------------------
ordered = []
while vector_paths:
    if not ordered:
        ordered.append(vector_paths.pop(0))
    else:
        last = ordered[-1]
        idx = min(
            range(len(vector_paths)),
            key=lambda i: np.linalg.norm(last[-1] - vector_paths[i][0])
        )
        ordered.append(vector_paths.pop(idx))

#--- Connecting to Arduino ---------------------------------------------------------------------------------------------------
ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
time.sleep(2)

def send(cmd):
    ser.write(cmd.encode())
    ser.flush()
    start = time.time()
    while time.time() - start < 5:  # 5 second timeout
        if ser.in_waiting > 0:
            line = ser.readline().decode().strip()
            if line == "OK":
                return
    print(f"Timeout waiting for OK after: {cmd.strip()}")

# #--- Homing Sequence ---------------------------------------------------------------------------------------------------------
print("Press ENTER to start drawing or Ctrl+C to cancel")
input()

# #--- Send Commands -----------------------------------------------------------------------------------------------------------
try:
    for path in ordered:
        x0, y0 = to_mm(path[0])
        x0 = np.clip(x0, 0, ANCHOR_WIDTH_MM)
        y0 = np.clip(y0, 0, MAX_Y_MM)

        send(PEN_UP)
        send(MOVE_CMD.format(x0, y0))
        send(PEN_DOWN)

        for pt in path[1:]:
            x, y = to_mm(pt)
            x = np.clip(x, 0, ANCHOR_WIDTH_MM)
            y = np.clip(y, 0, MAX_Y_MM)
            send(MOVE_CMD.format(x, y))

except KeyboardInterrupt:
    send(PEN_UP)

finally:
    send(PEN_UP)
    ser.close()
    print("Done.")

#
#--- Preview Path ------------------------------------------------------------------------------------------------------------
# canvas = np.zeros_like(img)
#
# def as_point(pt):
#     return int(pt[0]), int(pt[1])
#
# for path in vector_paths:
#     path = np.array(path)
#     if len(path) < 2:
#         continue
#     for i in range(len(path)):
#         pt1 = as_point(path[i])
#         pt2 = as_point(path[(i + 1) % len(path)])  # wrap around for closed contour
#         cv2.line(canvas, pt1, pt2, 255, 1)
#
# cv2.imshow("Vectorized Preview", canvas)
# cv2.waitKey(0)
# cv2.destroyAllWindows()