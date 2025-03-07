import RPi.GPIO as GPIO
import time
import cv2
import mediapipe as mp
import subprocess
import numpy as np
from twilio.rest import Client

# Define GPIO pin
SOLENOID_PIN = 18  

# Setup GPIO
GPIO.setmode(GPIO.BCM)  # Use Broadcom pin-numbering
GPIO.setup(SOLENOID_PIN, GPIO.OUT)

# Twilio configuration
account_sid = '#'
auth_token = '#'
twilio_number = '#'
recipient_number = '#'

client = Client(account_sid, auth_token)

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False, model_complexity=2, smooth_landmarks=True, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

def unlock_door():
    """Keeps the solenoid lock activated until the program exits."""
    print("Unlocking door...")
    GPIO.output(SOLENOID_PIN, GPIO.HIGH)  # Activate solenoid

def capture_image():
    command = [
        'libcamera-still', '--width', '640', '--height', '480', '--output', 'capture.jpg', '--nopreview'
    ]
    subprocess.run(command)
    return cv2.imread('capture.jpg')

def detect_fall(landmarks):
    try:
        required_landmarks = [
            mp_pose.PoseLandmark.LEFT_SHOULDER.value,
            mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
            mp_pose.PoseLandmark.LEFT_HIP.value,
            mp_pose.PoseLandmark.RIGHT_HIP.value,
            mp_pose.PoseLandmark.LEFT_KNEE.value,
            mp_pose.PoseLandmark.RIGHT_KNEE.value
        ]
        
        # Ensure all required landmarks are clearly visible
        if not all(landmarks[i].visibility > 0.7 for i in required_landmarks):
            return False  
        
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
        left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
        right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value]
        
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        knee_y = (left_knee.y + right_knee.y) / 2
        
        # Check if the person is in a fallen position
        if (hip_y - shoulder_y > 0.3) and (knee_y - hip_y > 0.2):
            
            # Additional check for sudden movement indicating a fall
            if abs(left_shoulder.y - left_hip.y) > 0.25 and abs(right_shoulder.y - right_hip.y) > 0.25:
                return True
    except:
        pass
    return False

def send_alert():
    message = client.messages.create(
        body='Fall detected! Immediate assistance may be required.',
        from_=twilio_number,
        to=recipient_number
    )
    print("Alert sent:", message.sid)

def main():
    fall_detected = False
    
    while not fall_detected:
        time.sleep(2.5)
        frame = capture_image()
        if frame is None:
            print("Error: No image captured.")
            continue
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(frame_rgb)
        
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            fall_detected = detect_fall(results.pose_landmarks.landmark)
            
            if fall_detected:
                send_alert()
                unlock_door()
                break
        else:
            print("Pose not detected properly. Adjusting camera angle or lighting might help.")
        
        cv2.imshow('Captured Image', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cv2.destroyAllWindows()
    GPIO.cleanup()
    print("Exiting program.")

if __name__ == "__main__":
    main()
