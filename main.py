import atexit
import time
import RPi.GPIO as GPIO

# ------------------ PIN MAP (BCM) ------------------ #
# Matches the BCM numbering in Notes/pinout.md.
ENA_PIN = 18  # GPIO18 / physical pin 12 (PWM0)
IN1_PIN = 17  # GPIO17 / physical pin 11
IN2_PIN = 27  # GPIO27 / physical pin 13

ENB_PIN = 13  # GPIO13 / physical pin 33 (PWM1)
IN3_PIN = 22  # GPIO22 / physical pin 15
IN4_PIN = 23  # GPIO23 / physical pin 16

# Sensor array GPIO inputs on the Pi (left -> right)
SENSOR_PINS = [2, 3, 4, 5, 6]
SENSOR_WEIGHTS = [-0.02, -0.01, 0.0, 0.01, 0.02]

# Drive tuning
BASE_SPEED = 0.55
STEER_GAIN = 8.0


# ------------------ SETUP ------------------ #
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(IN1_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(IN2_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(IN3_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(IN4_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(ENA_PIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(ENB_PIN, GPIO.OUT, initial=GPIO.LOW)
for sensor_pin in SENSOR_PINS:
    GPIO.setup(sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

ena_pwm = GPIO.PWM(ENA_PIN, 20000)
enb_pwm = GPIO.PWM(ENB_PIN, 20000)
ena_pwm.start(0)
enb_pwm.start(0)

print("Motors and sensors initialized")

# ------------------ MOTOR FUNCTIONS ------------------ #
def motor_a(speed):
    speed = max(-1, min(1, speed))  # clip to -1..1
    if speed > 0:
        GPIO.output(IN1_PIN, GPIO.HIGH)
        GPIO.output(IN2_PIN, GPIO.LOW)
        ena_pwm.ChangeDutyCycle(speed * 100.0)
    elif speed < 0:
        GPIO.output(IN1_PIN, GPIO.LOW)
        GPIO.output(IN2_PIN, GPIO.HIGH)
        ena_pwm.ChangeDutyCycle((-speed) * 100.0)
    else:
        GPIO.output(IN1_PIN, GPIO.LOW)
        GPIO.output(IN2_PIN, GPIO.LOW)
        ena_pwm.ChangeDutyCycle(0)

def motor_b(speed):
    speed = max(-1, min(1, speed))
    if speed > 0:
        GPIO.output(IN3_PIN, GPIO.HIGH)
        GPIO.output(IN4_PIN, GPIO.LOW)
        enb_pwm.ChangeDutyCycle(speed * 100.0)
    elif speed < 0:
        GPIO.output(IN3_PIN, GPIO.LOW)
        GPIO.output(IN4_PIN, GPIO.HIGH)
        enb_pwm.ChangeDutyCycle((-speed) * 100.0)
    else:
        GPIO.output(IN3_PIN, GPIO.LOW)
        GPIO.output(IN4_PIN, GPIO.LOW)
        enb_pwm.ChangeDutyCycle(0)


def get_sensor_feedback():
    # LOW means obstacle detected, matching sensor.py logic.
    feedback = 0.0
    detections = []
    for idx, sensor_pin in enumerate(SENSOR_PINS):
        is_obstacle = GPIO.input(sensor_pin) == GPIO.LOW
        if is_obstacle:
            feedback += SENSOR_WEIGHTS[idx]
            detections.append(idx)
    return feedback, detections


def apply_drive_from_feedback(feedback):
    steer = feedback * STEER_GAIN
    left_speed = max(-1.0, min(1.0, BASE_SPEED - steer))
    right_speed = max(-1.0, min(1.0, BASE_SPEED + steer))
    motor_a(left_speed)
    motor_b(right_speed)
    return left_speed, right_speed


def cleanup():
    motor_a(0)
    motor_b(0)
    try:
        ena_pwm.stop()
        enb_pwm.stop()
    except Exception:
        pass
    GPIO.cleanup()

# ------------------ MAIN LOOP ------------------ #
print("Starting main loop...")
atexit.register(cleanup)

try:
    while True:
        feedback, detections = get_sensor_feedback()
        left_speed, right_speed = apply_drive_from_feedback(feedback)
        print(
            f"Sensors hit: {detections} | feedback={feedback:+.3f} "
            f"| left={left_speed:+.2f} right={right_speed:+.2f}"
        )
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nStopping motors...")
finally:
    cleanup()



