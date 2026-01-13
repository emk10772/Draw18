import cv2
import numpy as np
import serial
import time

# ---------------- Setup ------------------------------------------------------------------------------------------------------
IMAGE_PATH = "NearnumJahanium.jpg"       # Input images
#IMAGE_PATH = "scotty.png"
#IMAGE_PATH = "drawing.png"
APPROX_EPSILON = 0.0001                  # Contour approximation accuracy (fraction of arc length)
SERIAL_PORT = "COM7"                     # Arduino COM port
BAUD = 115200
PEN_UP = "PEN_UP\n"
PEN_DOWN = "PEN_DOWN\n"
MOVE_CMD = "MOVE {} {}\n"
SCALE = 1.0                              # Scale from image pixels to robot coordinates

# --- Load & Threshold Image -------------------------------------------------------------------------------------------------
img = cv2.imread(IMAGE_PATH, cv2.IMREAD_GRAYSCALE)
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

#--- Connecting to Arduino ---------------------------------------------------------------------------------------------------
# ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
# time.sleep(2)
#
# def send(cmd):
#     ser.write(cmd.encode())
#     ser.flush()
#     time.sleep(0.01)  # small delay for Arduino to process
#
# #--- Homing Sequence ---------------------------------------------------------------------------------------------------------
# send(PEN_UP)
# send(MOVE_CMD.format(0, 0))
# print("Press ENTER to start drawing or Ctrl+C to cancel")
# input()
#
# #--- Send Commands -----------------------------------------------------------------------------------------------------------
# try:
#     for path in vector_paths:
#         path = np.array(path)
#         if len(path) < 2:
#             continue
#
#         # Move to start point with pen up
#         start_x = int(path[0][0] * SCALE)
#         start_y = int(path[0][1] * SCALE)
#         send(PEN_UP)
#         send(MOVE_CMD.format(start_x, start_y))
#
#         # Put pen down
#         send(PEN_DOWN)
#
#         # Draw the path
#         for point in path[1:]:
#             x = int(point[0] * SCALE)
#             y = int(point[1] * SCALE)
#             send(MOVE_CMD.format(x, y))
# except KeyboardInterrupt:
#     print("Drawing stopped")
#     send(PEN_UP)
#
# finally:
#     send(PEN_UP)
#     ser.close()
#     print("Drawing finished")
#
# #--- Preview Path ------------------------------------------------------------------------------------------------------------
canvas = np.zeros_like(img)

def as_point(pt):
    return int(pt[0]), int(pt[1])

for path in vector_paths:
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