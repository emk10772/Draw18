import cv2
import numpy as np
import serial
import time

# ---------------- Setup ------------------------------------------------------------------------------------------------------
#Image processing
IMAGE_PATH = "NearnumJahanium.jpg"       # Input images
#IMAGE_PATH = "scotty.png"
#IMAGE_PATH = "drawing.png"
APPROX_EPSILON = 0.0001                  # Contour approximation accuracy (fraction of arc length)

#Arduino connection
SERIAL_PORT = "COM3"                     # Arduino COM port
BAUD = 115200

#Commands
PEN_UP = "PEN_UP\n"
PEN_DOWN = "PEN_DOWN\n"
MOVE_CMD = "MOVE {:.2f} {:.2f}\n"

# Whiteboard dimensions
BOARD_WIDTH_MM = 490
BOARD_HEIGHT_MM = 855

# Drawing area
DRAW_WIDTH_MM = 290
DRAW_HEIGHT_MM = 375

#Area offset
OFFSET_X_MM = 100   #100mm from left string
OFFSET_Y_MM = 240   #240mm from top of strings

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
SCALE_X = DRAW_WIDTH_MM / w
SCALE_Y = DRAW_HEIGHT_MM / h
SCALE = min(SCALE_X, SCALE_Y)  # Keep aspect ratio

def to_mm(pt):
    x = (pt[0] * SCALE) + OFFSET_X_MM
    y = (pt[1] * SCALE) + OFFSET_Y_MM
    return x, y

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
#
# def send(cmd):
#     ser.write(cmd.encode())
#     ser.flush()
#     start = time.time()
#     while time.time() - start < 3:  # 8 second timeout
#         if ser.in_waiting > 0:
#             line = ser.readline().decode().strip()
#             if line == "OK":
#                 return
#     print(f"Timeout waiting for OK after: {cmd.strip()}")

# #--- Start Drawing -----------------------------------------------------------------------------------------------------------
print("Press ENTER to start drawing or Ctrl+C to cancel")
input()

# #--- Send Commands -----------------------------------------------------------------------------------------------------------
# try:
#     for i, path in enumerate(ordered):
#         x0, y0 = to_mm(path[0])
#         # Clamp to drawing area bounds
#         x0 = np.clip(x0, OFFSET_X_MM, OFFSET_X_MM + DRAW_WIDTH_MM)
#         y0 = np.clip(y0, OFFSET_Y_MM, OFFSET_Y_MM + DRAW_HEIGHT_MM)
#
#         send(PEN_UP)
#         send(MOVE_CMD.format(x0, y0))
#         send(PEN_DOWN)
#
#         for pt in path[1:]:
#             x, y = to_mm(pt)
#             # Clamp to drawing area bounds
#             x = np.clip(x, OFFSET_X_MM, OFFSET_X_MM + DRAW_WIDTH_MM)
#             y = np.clip(y, OFFSET_Y_MM, OFFSET_Y_MM + DRAW_HEIGHT_MM)
#             send(MOVE_CMD.format(x, y))
#
# except KeyboardInterrupt:
#     print("Drawing terminated")
#     send(PEN_UP)
#
# finally:
#     send(PEN_UP)
#     ser.close()
#     print("Drawing finished")
#

#--- Preview Path ------------------------------------------------------------------------------------------------------------
canvas = np.zeros_like(img)

def as_point(pt):
    return int(pt[0]), int(pt[1])

for path in ordered:
    path = np.array(path)
    if len(path) < 2:
        continue
    for i in range(len(path)):
        pt1 = as_point(path[i])
        pt2 = as_point(path[(i + 1) % len(path)])  # wrap around for closed contour
        cv2.line(canvas, pt1, pt2, 255, 1)

cv2.imshow("Vectorized Preview", canvas)
cv2.waitKey(0)
cv2.destroyAllWindows()