import cv2
import numpy as np
import serial
import time

# ---------------- Setup ---------------------------------------------------------------------------------------------------------------------------------------
#IMAGE_PATH = "drawing.png"
#IMAGE_PATH = "scotty.webp"
IMAGE_PATH = "NearnumJahanian.jpg"
#IMAGE_PATH = "build18.jpg"
SERIAL_PORT = "COM3"
BAUD = 115200

# Commands
PEN_UP = "PEN_UP\n"
PEN_DOWN = "PEN_DOWN\n"
MOVE_CMD = "MOVE {:.2f} {:.2f}\n"

# Board Dimensions
BOARD_WIDTH_MM = 508
BOARD_HEIGHT_MM = 864
DRAW_WIDTH_MM = 254
DRAW_HEIGHT_MM = 241
OFFSET_X_MM = 127
OFFSET_Y_MM = 419

# --- Edge Detection & Pixel Following -------------------------------------------------------------------------------------------------------------------------

# Import image
img = cv2.imread(IMAGE_PATH, cv2.IMREAD_GRAYSCALE)
h, w = img.shape

# Threshold
binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 9, 10)

# Thin to skeleton
thinned = cv2.ximgproc.thinning(binary, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)


# Find endpoints and junctions
def get_neighbors(y, x, img):
    neighbors = []
    for dy in [-1, 0, 1]:
        for dx in [-1, 0, 1]:
            if dy == 0 and dx == 0:
                continue
            ny, nx = y + dy, x + dx
            if 0 <= ny < img.shape[0] and 0 <= nx < img.shape[1]:
                neighbors.append((ny, nx, img[ny, nx]))
    return neighbors

# Line tracing (Finds next unvisited white pixel)
def trace_line(start_y, start_x, skeleton, visited):
    path = [(start_x, start_y)]
    visited[start_y, start_x] = True

    current_y, current_x = start_y, start_x

    while True:
        # Find next unvisited neighbor
        neighbors = get_neighbors(current_y, current_x, skeleton)
        next_point = None

        for ny, nx, val in neighbors:
            if val > 0 and not visited[ny, nx]:
                next_point = (ny, nx)
                break

        if next_point is None:
            break  # End of line

        current_y, current_x = next_point
        path.append((current_x, current_y))  # (x, y)
        visited[current_y, current_x] = True

    return path


# Extract paths by tracing skeleton
visited = np.zeros_like(thinned, dtype=bool)
vector_paths = []

# Find all white pixels
white_pixels = np.argwhere(thinned > 0)

for y, x in white_pixels:
    if not visited[y, x]:
        path = trace_line(y, x, thinned, visited)
        if len(path) > 5:  # Filter short paths
            vector_paths.append(np.array(path))

# Simplify paths using Douglas-Peucker
simplified_paths = []
for path in vector_paths:
    # Convert to format OpenCV expects
    path_reshaped = path.reshape(-1, 1, 2).astype(np.float32)
    epsilon = 0.01 # Smaller epsilon = More precise image
    approx = cv2.approxPolyDP(path_reshaped, epsilon, False)
    approx = approx.reshape(-1, 2)

    if len(approx) >= 2:
        simplified_paths.append(approx)

# --- Scaling ---------------------------------------------------------------------------------------------------------------------------------------------------
SCALE_X = DRAW_WIDTH_MM / w
SCALE_Y = DRAW_HEIGHT_MM / h
SCALE = min(SCALE_X, SCALE_Y)

def to_mm(pt):
    x = (pt[0] * SCALE) + OFFSET_X_MM
    y = (pt[1] * SCALE) + OFFSET_Y_MM
    return x, y

# --- Ordering -------------------------------------------------------------------------------------------------------------------------------------------------
ordered = []
remaining = simplified_paths.copy()

if remaining:
    ordered.append(remaining.pop(0))

    while remaining:
        last = ordered[-1]
        idx = min(
            range(len(remaining)),
            key=lambda i: np.linalg.norm(last[-1] - remaining[i][0])
        )
        ordered.append(remaining.pop(idx))

print(f"Ordered {len(ordered)} paths")

# --- Preview ---------------------------------------------------------------------------------------------------------------------------------------------------
canvas = np.zeros_like(img)

for path in ordered:
    for i in range(len(path) - 1):
        pt1 = tuple(path[i].astype(int))
        pt2 = tuple(path[i + 1].astype(int))
        cv2.line(canvas, pt1, pt2, 255, 1)

cv2.imshow("Traced Paths - Press any key", canvas)

# --- Arduino Connection ----------------------------------------------------------------------------------------------------------------------------------------
print("Connecting to Arduino...")
ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
time.sleep(2)

def send(cmd):
    ser.write(cmd.encode())
    ser.flush()
    start = time.time()
    while time.time() - start < 5:
        if ser.in_waiting > 0:
            if ser.readline().decode().strip() == "OK":
                return

print("Press ENTER to start drawing")
input()

# --- Drawing ---------------------------------------------------------------------------------------------------------------------------------------------------
try:
    for i, path in enumerate(ordered):
        if len(path) < 2:
            continue

        x0, y0 = to_mm(path[0])
        x0 = np.clip(x0, OFFSET_X_MM, OFFSET_X_MM + DRAW_WIDTH_MM)
        y0 = np.clip(y0, OFFSET_Y_MM, OFFSET_Y_MM + DRAW_HEIGHT_MM)

        send(PEN_UP)
        send(MOVE_CMD.format(x0, y0))
        send(PEN_DOWN)

        for pt in path[1:]:
            x, y = to_mm(pt)
            x = np.clip(x, OFFSET_X_MM, OFFSET_X_MM + DRAW_WIDTH_MM)
            y = np.clip(y, OFFSET_Y_MM, OFFSET_Y_MM + DRAW_HEIGHT_MM)
            send(MOVE_CMD.format(x, y))

except KeyboardInterrupt:
    print("\nTerminated")
    send(PEN_UP)

finally:
    send(PEN_UP)
    send(MOVE_CMD.format(254, 660))
    ser.close()
    print("Drawing finished")