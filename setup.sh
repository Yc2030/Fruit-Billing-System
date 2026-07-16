#!/bin/bash

set -e

echo "======================================="
echo " Fruit Billing System Setup"
echo "======================================="

echo "[1/7] Updating package lists..."
sudo apt update

echo "[2/7] Installing system packages..."
sudo apt install -y \
python3-pip \
python3-venv \
python3-opencv \
python3-dev \
build-essential \
git \
ffmpeg \
espeak \
espeak-ng \
libatlas-base-dev \
libopenblas-dev \
libjpeg-dev \
libtiff-dev \
libavcodec-dev \
libavformat-dev \
libswscale-dev \
libgtk-3-dev \
libcanberra-gtk3-module \
libportaudio2 \
portaudio19-dev \
zip \
unzip

echo "[3/7] Creating Python virtual environment..."
python3 -m venv yolo_env

echo "[4/7] Activating virtual environment..."
source yolo_env/bin/activate

echo "[5/7] Upgrading pip..."
pip install --upgrade pip

echo "[6/7] Installing Python packages..."
pip install -r requirements.txt

echo "[7/7] Setup complete."

echo
echo "======================================="
echo "Installation Successful!"
echo "======================================="
echo
echo "To run the project:"
echo
echo "source yolo_env/bin/activate"
echo "python billingsys.py"
