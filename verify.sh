#!/bin/bash

echo "======================================="
echo " Fruit Billing System Verification"
echo "======================================="

ERRORS=0
PROJECT_DIR="$HOME/FruitBilling_Project"

check_ok() {
    echo "[OK] $1"
}

check_fail() {
    echo "[MISSING] $1"
    ERRORS=$((ERRORS + 1))
}

echo
echo "Checking project files..."

[ -f "$PROJECT_DIR/billingsys.py" ] \
    && check_ok "billingsys.py" \
    || check_fail "billingsys.py"

[ -f "$PROJECT_DIR/requirements.txt" ] \
    && check_ok "requirements.txt" \
    || check_fail "requirements.txt"

[ -f "$PROJECT_DIR/positions.json" ] \
    && check_ok "positions.json" \
    || check_fail "positions.json"

[ -f "$PROJECT_DIR/setup.sh" ] \
    && check_ok "setup.sh" \
    || check_fail "setup.sh"

[ -f "$PROJECT_DIR/runs/detect/train12/weights/best.pt" ] \
    && check_ok "YOLO model best.pt" \
    || check_fail "runs/detect/train12/weights/best.pt"

echo
echo "Checking Python environment..."

if [ -d "$HOME/yolo_env" ]; then
    check_ok "yolo_env virtual environment"
else
    check_fail "yolo_env virtual environment"
fi

if "$HOME/yolo_env/bin/python" -c "import ultralytics" 2>/dev/null; then
    check_ok "Ultralytics"
else
    check_fail "Ultralytics"
fi

if "$HOME/yolo_env/bin/python" -c "import torch" 2>/dev/null; then
    check_ok "Torch"
else
    check_fail "Torch"
fi

if "$HOME/yolo_env/bin/python" -c "import cv2" 2>/dev/null; then
    check_ok "OpenCV"
else
    check_fail "OpenCV"
fi

if "$HOME/yolo_env/bin/python" -c "import serial" 2>/dev/null; then
    check_ok "PySerial"
else
    check_fail "PySerial"
fi

if "$HOME/yolo_env/bin/python" -c "from pydobot import Dobot" 2>/dev/null; then
    check_ok "pydobot"
else
    check_fail "pydobot"
fi

echo
echo "Checking hardware..."

if [ -e /dev/video0 ]; then
    check_ok "Camera detected at /dev/video0"
else
    check_fail "Camera at /dev/video0"
fi

if compgen -G "/dev/ttyACM*" > /dev/null; then
    check_ok "Dobot serial port detected"
elif compgen -G "/dev/ttyUSB*" > /dev/null; then
    check_ok "USB serial port detected"
else
    check_fail "Dobot serial port"
fi

echo
echo "======================================="

if [ "$ERRORS" -eq 0 ]; then
    echo "Fruit Billing System is ready."
    exit 0
else
    echo "$ERRORS check(s) failed."
    echo "Review the missing items above."
    exit 1
fi
