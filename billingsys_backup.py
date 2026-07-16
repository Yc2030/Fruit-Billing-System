from ultralytics import YOLO
import cv2
from pydobot import Dobot
import json
import os
import time
import RPi.GPIO as GPIO
from gtts import gTTS

# ---------------------------
# GPIO SETUP
# ---------------------------
CONVEYOR_PIN = 17
IR_PIN = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(CONVEYOR_PIN, GPIO.OUT)
GPIO.setup(IR_PIN, GPIO.IN)

# ---------------------------
# CONVEYOR
# ---------------------------
def conveyor_on():
    GPIO.output(CONVEYOR_PIN, GPIO.HIGH)
    print("🟢 Conveyor ON")

def conveyor_off():
    GPIO.output(CONVEYOR_PIN, GPIO.LOW)
    print("🔴 Conveyor OFF")

# ---------------------------
# VOICE
# ---------------------------
def speak(text):
    print("🔊", text)
    try:
        tts = gTTS(text=text, lang='en')
        tts.save("voice.mp3")
        os.system("mpg123 -q voice.mp3")
    except Exception as e:
        print("Voice error:", e)

# ---------------------------
# DOBOT
# ---------------------------
device = Dobot(port='/dev/ttyACM0')

# ---------------------------
# LOAD POSITIONS
# ---------------------------
with open("positions.json", "r") as f:
    positions = json.load(f)

print("✅ Positions loaded")

# ---------------------------
# MODEL
# ---------------------------
model = YOLO("/home/simusoft_technology/runs/detect/train12/weights/best.pt")
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ---------------------------
# STATE VARIABLES
# ---------------------------
stable_label = None
stable_count = 0
robot_busy = False
ir_triggered = False

# ---------------------------
# GRIPPER
# ---------------------------
def gripper_open():
    device.grip(True)
    print("✋ OPEN")

def gripper_close():
    device.grip(False)
    print("✊ CLOSE")

# ---------------------------
# DROP MAP
# ---------------------------
drop_map = {
    "pear": "pear_drop",
    "strawberry": "strawberry_drop",
    "pineapple": "pineapple_drop",
    "orange": "orange_drop"
}

# ---------------------------
# COUNTER
# ---------------------------
fruit_counts = {
    "pear": 0,
    "strawberry": 0,
    "pineapple": 0,
    "orange": 0
}

# ---------------------------
# START SAFE STATE
# ---------------------------
conveyor_off()

# ---------------------------
# MAIN LOOP
# ---------------------------
while True:

    ret, frame = cap.read()
    if not ret:
        continue

    # ---------------------------
    # YOLO DETECTION
    # ---------------------------
    if not robot_busy:

        results = model(frame, conf=0.5, imgsz=320)
        detected_label = None

        for r in results:
            frame = r.plot()

            for box in r.boxes:
                cls = int(box.cls[0])
                detected_label = model.names[cls]

        # ---------------------------
        # STABILITY CHECK
        # ---------------------------
        if detected_label == stable_label:
            stable_count += 1
        else:
            stable_label = detected_label
            stable_count = 0

        # ---------------------------
        # TRIGGER
        # ---------------------------
        if stable_count >= 5 and stable_label is not None:

            print("🎯 DETECTED:", stable_label)
            robot_busy = True

            # VOICE FIRST
            speak(f"This is {stable_label}")

            # START CONVEYOR
            conveyor_on()

            ir_triggered = False

    # ---------------------------
    # IR SENSOR CHECK (NON-BLOCKING)
    # ---------------------------
    if robot_busy and not ir_triggered:

        if GPIO.input(IR_PIN) == 0:
            ir_triggered = True

            print("📍 IR Triggered")

            conveyor_off()

            # COUNT UPDATE
            if stable_label in fruit_counts:
                fruit_counts[stable_label] += 1

            # ---------------------------
            # DOBOT PICK
            # ---------------------------
            gripper_open()
            device.move_to(*positions["pick_safe"], wait=True)
            device.move_to(*positions["pick"], wait=True)
            gripper_close()
            time.sleep(1)
            device.move_to(*positions["pick_safe"], wait=True)

            # ---------------------------
            # DROP
            # ---------------------------
            drop_key = drop_map.get(stable_label)

            if drop_key:
                device.move_to(*positions["drop_safe"], wait=True)
                device.move_to(*positions[drop_key], wait=True)

                gripper_open()
                time.sleep(1)

                device.move_to(*positions["drop_safe"], wait=True)

            # ---------------------------
            # HOME
            # ---------------------------
            device.move_to(*positions["home"], wait=True)

            print("✅ CYCLE COMPLETE")

            # RESET STATE
            stable_label = None
            stable_count = 0
            robot_busy = False
            ir_triggered = False

    # ---------------------------
    # DISPLAY COUNTS
    # ---------------------------
    y = 30
    for fruit, count in fruit_counts.items():
        cv2.putText(frame, f"{fruit}: {count}",
                    (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2)
        y += 30

    cv2.imshow("Detection", frame)

    if cv2.waitKey(1) == 27:
        break

# ---------------------------
# CLEANUP
# ---------------------------
cap.release()
cv2.destroyAllWindows()
GPIO.cleanup()
