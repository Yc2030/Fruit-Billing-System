#!/usr/bin/env python3

import argparse
import os
import json
import time
import threading
import glob

import cv2
import numpy as np
import RPi.GPIO as GPIO
from pydobot import Dobot

# ---------------- PORT DETECTION ----------------
def find_dobot_port():
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    if not ports:
        print("[PORT] No Dobot found")
        return None
    print("[PORT] Using:", ports[0])
    return ports[0]

# ---------------- CONFIG ----------------
RELAY_PIN = 17
CONFIG_FILE = "dobot_coords.json"

PICK_SAFE_Z_OFFSET = 100
PLACE_Z = None

CONVEYOR_DELAY = 5.0
CONVEYOR_MAX = 7.0

# ---------------- HSV ----------------
LOWER_RED1  = np.array([0, 100, 80])
UPPER_RED1  = np.array([10, 255, 255])
LOWER_RED2  = np.array([170, 100, 80])
UPPER_RED2  = np.array([180, 255, 255])

LOWER_BLUE  = np.array([90, 100, 80])
UPPER_BLUE  = np.array([130, 255, 255])

# Yellow object shade from your photo
LOWER_YELLOW = np.array([20, 120, 120])
UPPER_YELLOW = np.array([40, 255, 255])

LOWER_SKIN  = np.array([0, 30, 60])
UPPER_SKIN  = np.array([25, 170, 255])

# ---------------- RELAY ----------------
_relay_timer = None
_relay_lock = threading.Lock()

def _hard_cutoff():
    with _relay_lock:
        GPIO.output(RELAY_PIN, GPIO.LOW)
    print("[CONVEYOR] HARD CUT OFF")

def conveyor_on():
    global _relay_timer
    with _relay_lock:
        if _relay_timer:
            _relay_timer.cancel()

        GPIO.output(RELAY_PIN, GPIO.HIGH)
        _relay_timer = threading.Timer(CONVEYOR_MAX, _hard_cutoff)
        _relay_timer.daemon = True
        _relay_timer.start()

    print("[CONVEYOR] ON")

def conveyor_off():
    global _relay_timer
    with _relay_lock:
        if _relay_timer:
            _relay_timer.cancel()
            _relay_timer = None
        GPIO.output(RELAY_PIN, GPIO.LOW)

    print("[CONVEYOR] OFF")

# ---------------- GPIO ----------------
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.output(RELAY_PIN, GPIO.LOW)

def cleanup_gpio():
    conveyor_off()
    GPIO.cleanup()

# ---------------- CAMERA ----------------
def init_camera(index=0):
    cam = cv2.VideoCapture(index)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    if not cam.isOpened():
        raise RuntimeError("Camera not found")

    print("[CAM] OK")
    return cam

def get_frame(cam):
    for _ in range(2):
        cam.grab()
    ok, frame = cam.read()
    return frame if ok else None

# ---------------- DETECTION ----------------
def detect_color(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    mask_r = cv2.bitwise_or(
        cv2.inRange(hsv, LOWER_RED1, UPPER_RED1),
        cv2.inRange(hsv, LOWER_RED2, UPPER_RED2)
    )

    mask_b = cv2.inRange(hsv, LOWER_BLUE, UPPER_BLUE)
    mask_y = cv2.inRange(hsv, LOWER_YELLOW, UPPER_YELLOW)

    scores = {
        "Red": cv2.countNonZero(mask_r),
        "Blue": cv2.countNonZero(mask_b),
        "Yellow": cv2.countNonZero(mask_y)
    }

    best = max(scores, key=scores.get)

    if scores[best] > 800:
        print("[DETECT]", best, scores)
        return best

    return None

def has_hand(roi):
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_SKIN, UPPER_SKIN)
    return cv2.countNonZero(mask) > 800

# ---------------- ROBOT ----------------
def move_to(device, x, y, z, r=0):
    device.move_to(x, y, z, r, wait=True)
    time.sleep(0.3)

def pick_and_place(device, coords, color):
    pick = coords["PICK"]
    safe_z = pick["z"] + PICK_SAFE_Z_OFFSET

    print("[ROBOT] Pick:", color)

    move_to(device, pick["x"], pick["y"], safe_z)
    move_to(device, pick["x"], pick["y"], pick["z"])

    device.suck(True)
    time.sleep(0.5)

    move_to(device, pick["x"], pick["y"], safe_z)

    bin_map = {
        "Red": "BIN_RED",
        "Blue": "BIN_BLUE",
        "Yellow": "BIN_YELLOW"
    }

    if color not in bin_map:
        print("[ERROR] Unknown color:", color)
        return

    bin_key = bin_map[color]

    if bin_key not in coords:
        print("[ERROR] Missing calibration for:", bin_key)
        print("[FIX] Run: python3 sorter.py --calibrate")
        return

    b = coords[bin_key]
    target_z = PLACE_Z if PLACE_Z else b["z"]

    move_to(device, b["x"], b["y"], safe_z)
    move_to(device, b["x"], b["y"], target_z)

    device.suck(False)
    time.sleep(0.5)

    move_to(device, pick["x"], pick["y"], safe_z)

# ---------------- CALIBRATION ----------------
def calibrate(device):
    print("\n[CALIBRATION MODE]")
    coords = {}

    for key in ["PICK", "BIN_RED", "BIN_BLUE", "BIN_YELLOW"]:
        input(f"Move robot to {key}, then press ENTER...")

        pose = device.pose()
        coords[key] = {
            "x": round(pose[0], 2),
            "y": round(pose[1], 2),
            "z": round(pose[2], 2),
            "r": round(pose[3], 2),
        }

        print("[SAVED]", key, coords[key])

    with open(CONFIG_FILE, "w") as f:
        json.dump(coords, f, indent=4)

    print("[CALIB] Saved to file")
    return coords

# ---------------- MAIN ----------------
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--calibrate", action="store_true",
                        help="Run calibration before start")

    args = parser.parse_args()

    print("[INIT] Connecting Dobot...")

    device = None
    PORT = None

    for _ in range(10):
        PORT = find_dobot_port()
        if PORT:
            try:
                device = Dobot(port=PORT, verbose=False)
                print("[INIT] Connected:", PORT)
                break
            except Exception as e:
                print("[INIT] Connection failed:", e)

        time.sleep(2)

    if device is None:
        raise RuntimeError("Dobot not found")

    if args.calibrate or not os.path.exists(CONFIG_FILE):
        coords = calibrate(device)
    else:
        with open(CONFIG_FILE, "r") as f:
            coords = json.load(f)
        print("[INIT] Loaded calibration")

    required_keys = ["PICK", "BIN_RED", "BIN_BLUE", "BIN_YELLOW"]
    missing = [key for key in required_keys if key not in coords]

    if missing:
        print("[ERROR] Calibration file is missing:", missing)
        print("[FIX] Run calibration again:")
        print("python3 sorter.py --calibrate")
        device.close()
        return

    setup_gpio()
    cam = init_camera(args.camera_index)

    state = "IDLE"
    detected = None
    start_time = None

    try:
        while True:
            frame = get_frame(cam)
            if frame is None:
                continue

            h, w, _ = frame.shape
            roi = frame[h//4:3*h//4, w//4:3*w//4]

            color = detect_color(roi)
            hand = has_hand(roi)

            if state == "IDLE":
                if color and not hand:
                    time.sleep(1.5)

                    detected = color
                    conveyor_on()
                    start_time = time.time()
                    state = "RUN"

            elif state == "RUN":
                if time.time() - start_time >= CONVEYOR_DELAY:
                    conveyor_off()

                    if detected:
                        pick_and_place(device, coords, detected)

                    detected = None
                    state = "WAIT"

            elif state == "WAIT":
                if color is None:
                    state = "IDLE"

    except KeyboardInterrupt:
        print("[STOP] User")

    finally:
        cam.release()
        device.close()
        cleanup_gpio()
        cv2.destroyAllWindows()
        print("[EXIT] Clean shutdown")

if __name__ == "__main__":
    main()