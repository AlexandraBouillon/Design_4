from machine import Pin, PWM, ADC
import time

print("Initializing motor control system...")

# Voltage monitoring setup
# Note: VSYS monitoring via ADC may not be available on all Pico boards
# If VSYS reading doesn't work, you can measure supply voltage externally with a multimeter
# or use an external voltage divider on a regular ADC pin (e.g., GP26 or GP27)
try:
    vsys_adc = ADC(Pin(29))
    # Test if the reading is valid
    test_read = vsys_adc.read_u16()
    if test_read >= 65500:  # If saturated, it's not working
        vsys_adc = None
        print("VSYS monitoring: Pin 29 not accessible (feature may not be available on this board)")
    else:
        print("VSYS monitoring: Using ADC on Pin 29")
except:
    try:
        vsys_adc = ADC(3)
        test_read = vsys_adc.read_u16()
        if test_read >= 65500:
            vsys_adc = None
            print("VSYS monitoring: ADC channel 3 not accessible")
        else:
            print("VSYS monitoring: Using ADC channel 3")
    except:
        vsys_adc = None
        print("VSYS monitoring: Not available on this board")

# VSYS divider: The Pico has a 3:1 divider, so VSYS = ADC_reading * 3
VSYS_DIVIDER_RATIO = 3.0  # Internal divider ratio for VSYS
ADC_MAX = 65535  # 16-bit ADC max value
VREF = 3.3       # ADC reference voltage
VSYS_AVAILABLE = vsys_adc is not None

# Alternative: Pico supply voltage via external voltage divider (if VSYS doesn't work)
# Use this if you want to measure Pico supply voltage with external hardware
PICO_VOLTAGE_EXTERNAL_AVAILABLE = False  # Set to True when hardware is connected
# pico_voltage_adc = ADC(27)  # Use a different ADC pin (e.g., GP27)
# PICO_DIVIDER_RATIO = 2.0     # For 2x 10kΩ resistors (divides by 2)

# For motor voltage monitoring (requires external voltage divider on an ADC pin)
# 
# SETUP INSTRUCTIONS:
# 1. You need 2x 10kΩ (10,000 ohm) resistors - NOT 10 ohm!
# 2. Connect: Motor Supply (+) -> R1 (10kΩ) -> ADC Pin -> R2 (10kΩ) -> GND
# 3. For 12V motors: Use R1=30kΩ, R2=10kΩ (ratio 4.0) to keep ADC under 3.3V
# 4. For 6V motors: Use R1=10kΩ, R2=10kΩ (ratio 2.0)
# 
# Once hardware is connected, uncomment and configure below:
MOTOR_VOLTAGE_AVAILABLE = False  # Set to True when hardware is connected
# motor_voltage_adc = ADC(26)  # Change to GP26, GP27, or another ADC pin
# MOTOR_DIVIDER_RATIO = 2.0    # 2.0 for equal resistors, 4.0 for 12V with 30k/10k

# Motor A (Left Motor) - L298N connections
# ENA = GP0, IN1 = GP1, IN2 = GP2
print("Setting up Motor A (ENA: Pin 0, IN1: Pin 1, IN2: Pin 2)")
ena = PWM(Pin(0))
in1 = Pin(1, Pin.OUT)
in2 = Pin(2, Pin.OUT)
# Initialize both direction pins to LOW
in1.low()
in2.low()
print(f"  Motor A pins initialized: IN1={in1.value()}, IN2={in2.value()}")

# Motor B (Right Motor) - L298N connections  
# ENB = GP5, IN3 = GP3, IN4 = GP4
print("Setting up Motor B (ENB: Pin 5, IN3: Pin 3, IN4: Pin 4)")
enb = PWM(Pin(5))
in3 = Pin(3, Pin.OUT)
in4 = Pin(4, Pin.OUT)
# Initialize both direction pins to LOW
in3.low()
in4.low()
print(f"  Motor B pins initialized: IN3={in3.value()}, IN4={in4.value()}")

ena.freq(20000)
enb.freq(20000)
print("PWM frequency set to 20000 Hz for both motors")

# Initialize PWM to 0 (stopped)
ena.duty_u16(0)
enb.duty_u16(0)
print("PWM initialized to 0 (motors stopped)")

# Voltage reading functions
def read_pico_voltage():
    """Read Pico VSYS voltage using built-in ADC(3) or Pin(29), or external ADC"""
    # Try built-in VSYS first
    if VSYS_AVAILABLE:
        raw = vsys_adc.read_u16()
        # Check if reading is valid (not saturated)
        if raw < ADC_MAX - 100:  # Valid reading
            voltage_at_adc = (raw / ADC_MAX) * VREF
            vsys_voltage = voltage_at_adc * VSYS_DIVIDER_RATIO
            return vsys_voltage, raw
    
    # Try external ADC if VSYS doesn't work
    if PICO_VOLTAGE_EXTERNAL_AVAILABLE:
        raw = pico_voltage_adc.read_u16()
        voltage_at_adc = (raw / ADC_MAX) * VREF
        pico_voltage = voltage_at_adc * PICO_DIVIDER_RATIO
        return pico_voltage, raw
    
    return None, 0

def read_motor_voltage():
    """Read motor supply voltage (requires external voltage divider)"""
    if not MOTOR_VOLTAGE_AVAILABLE:
        return None
    
    raw = motor_voltage_adc.read_u16()
    voltage_at_adc = (raw / ADC_MAX) * VREF
    motor_voltage = voltage_at_adc * MOTOR_DIVIDER_RATIO
    return motor_voltage

def print_voltages():
    """Print current voltage readings"""
    pico_v, raw_adc = read_pico_voltage()
    motor_v = read_motor_voltage()
    
    # Print Pico VSYS voltage
    if pico_v is not None:
        voltage_at_adc = (raw_adc / ADC_MAX) * VREF
        print(f"  Pico VSYS: {pico_v:.2f}V (ADC raw: {raw_adc})", end="")
    else:
        if not VSYS_AVAILABLE:
            print("  Pico VSYS: Not available on this board (use multimeter to measure)", end="")
        elif raw_adc >= ADC_MAX - 100:
            print("  Pico VSYS: Not accessible (use multimeter or external ADC pin)", end="")
        else:
            print("  Pico VSYS: Not available", end="")
    
    # Print motor voltage
    if motor_v is not None:
        print(f" | Motor Supply: {motor_v:.2f}V")
    else:
        print(" | Motor Supply: Not connected (requires voltage divider)")

print("Initialization complete!\n")

# ALTERNATIVE: If PWM doesn't work, try using enable pins as digital outputs
# Some L298N boards work better with enable pins set HIGH directly
# Uncomment below to test this alternative method:
USE_DIGITAL_ENABLE = False  # Set to True to use digital enable instead of PWM
if USE_DIGITAL_ENABLE:
    print("WARNING: Using digital enable mode (full speed only)")
    ena_digital = Pin(0, Pin.OUT)
    enb_digital = Pin(5, Pin.OUT)
    ena_digital.high()  # Enable motor A
    enb_digital.high()  # Enable motor B

def motor_a(speed):
    if speed > 0:
        print(f"Motor A: Forward at {speed*100:.1f}% speed")
        in1.high()
        in2.low()
        ena.duty_u16(int(speed * 65535))
    elif speed < 0:
        print(f"Motor A: Reverse at {abs(speed)*100:.1f}% speed")
        in1.low()
        in2.high()
        ena.duty_u16(int(-speed * 65535))
    else:
        print("Motor A: Stopped")
        # IMPORTANT: Set both pins low and PWM to 0 when stopping
        in1.low()
        in2.low()
        ena.duty_u16(0)

def motor_b(speed):
    if speed > 0:
        print(f"Motor B: Forward at {speed*100:.1f}% speed")
        in3.high()
        in4.low()
        enb.duty_u16(int(speed * 65535))
    elif speed < 0:
        print(f"Motor B: Reverse at {abs(speed)*100:.1f}% speed")
        in3.low()
        in4.high()
        enb.duty_u16(int(-speed * 65535))
    else:
        print("Motor B: Stopped")
        # IMPORTANT: Set both pins low and PWM to 0 when stopping
        in3.low()
        in4.low()
        enb.duty_u16(0)

def test_motor_pins():
    """Diagnostic function to test motor control pins"""
    print("\n=== DETAILED MOTOR DIAGNOSTIC TEST ===")
    
    print("\n--- Motor A Hardware Test ---")
    print("Step 1: Testing direction pins...")
    in1.high()
    in2.low()
    print(f"  IN1 (GP1): {in1.value()} (should be 1)")
    print(f"  IN2 (GP2): {in2.value()} (should be 0)")
    time.sleep(0.5)
    
    print("\nStep 2: Testing PWM enable...")
    ena.duty_u16(32767)  # 50% duty cycle
    actual_duty = ena.duty_u16()
    print(f"  ENA (GP0) PWM duty: {actual_duty} / 65535 ({actual_duty/65535*100:.1f}%)")
    print(f"  ENA PWM frequency: {ena.freq()} Hz")
    print("  Motor should be running now...")
    time.sleep(3)
    
    print("\nStep 3: Reversing direction...")
    in1.low()
    in2.high()
    print(f"  IN1 (GP1): {in1.value()} (should be 0)")
    print(f"  IN2 (GP2): {in2.value()} (should be 1)")
    time.sleep(3)
    
    print("\nStep 4: Stopping...")
    in1.low()
    in2.low()
    ena.duty_u16(0)
    time.sleep(0.1)  # Small delay to let pins settle
    print(f"  ENA duty: {ena.duty_u16()} (should be 0)")
    in1_val = in1.value()
    in2_val = in2.value()
    print(f"  IN1: {in1_val}, IN2: {in2_val} (both should be 0)")
    if in2_val != 0:
        print(f"  WARNING: IN2 (GP2) is reading {in2_val} but should be 0!")
        print(f"  This may indicate a wiring issue or pin conflict with GP2")
    
    print("\n--- Motor B Hardware Test ---")
    print("Step 1: Testing direction pins...")
    in3.high()
    in4.low()
    print(f"  IN3 (GP3): {in3.value()} (should be 1)")
    print(f"  IN4 (GP4): {in4.value()} (should be 0)")
    time.sleep(0.5)
    
    print("\nStep 2: Testing PWM enable...")
    enb.duty_u16(32767)  # 50% duty cycle
    actual_duty = enb.duty_u16()
    print(f"  ENB (GP5) PWM duty: {actual_duty} / 65535 ({actual_duty/65535*100:.1f}%)")
    print(f"  ENB PWM frequency: {enb.freq()} Hz")
    print("  Motor should be running now...")
    time.sleep(3)
    
    print("\nStep 3: Reversing direction...")
    in3.low()
    in4.high()
    print(f"  IN3 (GP3): {in3.value()} (should be 0)")
    print(f"  IN4 (GP4): {in4.value()} (should be 1)")
    time.sleep(3)
    
    print("\nStep 4: Stopping...")
    enb.duty_u16(0)
    in3.low()
    in4.low()
    print(f"  ENB duty: {enb.duty_u16()} (should be 0)")
    print(f"  IN3: {in3.value()}, IN4: {in4.value()} (both should be 0)")
    
    print("\n--- Testing Maximum Speed ---")
    print("Motor A at 100% speed...")
    in1.high()
    in2.low()
    ena.duty_u16(65535)  # 100% duty cycle
    print(f"  ENA duty: {ena.duty_u16()} (100%)")
    time.sleep(2)
    ena.duty_u16(0)
    
    print("Motor B at 100% speed...")
    in3.high()
    in4.low()
    enb.duty_u16(65535)  # 100% duty cycle
    print(f"  ENB duty: {enb.duty_u16()} (100%)")
    time.sleep(2)
    enb.duty_u16(0)
    in3.low()
    in4.low()
    
    print("\n=== DIAGNOSTIC TEST COMPLETE ===")
    print("\nTROUBLESHOOTING CHECKLIST:")
    print("  [ ] L298N VCC (logic) connected to 5V?")
    print("  [ ] L298N motor power connected to 6-7V?")
    print("  [ ] All GNDs connected together (common ground)?")
    print("  [ ] Motors connected to OUT1/OUT2 (Motor A) and OUT3/OUT4 (Motor B)?")
    print("  [ ] L298N enable jumpers removed (if present)?")
    print("  [ ] Check L298N board LED indicators (if any)")
    print("  [ ] Try swapping motor wires if motor direction is wrong")
    print("  [ ] Test motors directly: touch motor wires to 6V battery")
    print("  [ ] Verify pin connections with multimeter (check continuity)")
    print()

print("Starting motor test sequence...\n")
print("Initial voltage readings:")
print_voltages()
print()

# CRITICAL: Check for pin reading issues
print("=== PRE-FLIGHT PIN CHECK ===")
print("Verifying all pins can be read correctly...")
in1_test = in1.value()
in2_test = in2.value()
in3_test = in3.value()
in4_test = in4.value()
print(f"  Motor A: IN1={in1_test}, IN2={in2_test}")
print(f"  Motor B: IN3={in3_test}, IN4={in4_test}")

if in2_test != 0:
    print(f"\n  ⚠️  WARNING: IN2 (GP2) reads {in2_test} but should be 0!")
    print(f"  Possible causes:")
    print(f"    1. GP2 is being used elsewhere (check your wiring)")
    print(f"    2. Pin conflict or hardware issue")
    print(f"    3. L298N board issue")
print()

# IMPORTANT: Run diagnostic test first to check hardware
print("=== RUNNING HARDWARE DIAGNOSTIC TEST ===")
print("This will test all pins and PWM signals...")
print("Watch the motors - they should move during this test!")
print("If motors don't move, the issue is likely:")
print("  - L298N power supply (check VCC and motor power)")
print("  - Motor connections (check OUT1/OUT2 and OUT3/OUT4)")
print("  - L298N enable jumpers (remove if present)")
print("  - Ground connections (all GNDs must be connected)")
print()
test_motor_pins()

# Run a simple immediate test
print("\n=== QUICK MOTOR TEST ===")
print("Testing Motor A at 50% speed for 3 seconds...")
motor_a(0.5)
time.sleep(3)
motor_a(0)
print("Motor A test complete. Did it move?\n")

print("Testing Motor B at 50% speed for 3 seconds...")
motor_b(0.5)
time.sleep(3)
motor_b(0)
print("Motor B test complete. Did it move?\n")

print("\n=== CRITICAL CHECKS ===")
print("If motors STILL didn't move, verify:")
print("  1. L298N VCC (logic) = 5V from boost module")
print("  2. L298N Motor Power = 6-7V from boost module") 
print("  3. ALL GNDs connected together (Pico, L298N, boost module)")
print("  4. Motors connected: Motor A -> OUT1/OUT2, Motor B -> OUT3/OUT4")
print("  5. L298N enable jumpers REMOVED (if your board has them)")
print("  6. Check L298N board for LED power indicators")
print("  7. Try manually touching motor wires to battery to test motors")
print("\nStarting main test sequence in 3 seconds...\n")
time.sleep(3)

cycle = 1

while True:
    print(f"=== Test Cycle {cycle} ===")
    print_voltages()
    
    print("\n[Test 1] Both motors forward (straight)")
    motor_a(0.6)
    motor_b(0.6)
    print("Running for 2 seconds...")
    time.sleep(1)
    print_voltages()  # Check voltage during motor operation
    time.sleep(1)

    print("\n[Test 2] Stopping both motors")
    motor_a(0)
    motor_b(0)
    print("Stopped for 1 second...")
    time.sleep(1)
    print_voltages()  # Check voltage when stopped

    print("\n[Test 3] Motor A forward, Motor B reverse (turning)")
    motor_a(0.6)
    motor_b(-0.6)
    print("Running for 2 seconds...")
    time.sleep(1)
    print_voltages()  # Check voltage during turning
    time.sleep(1)

    print("\n[Test 4] Stopping both motors")
    motor_a(0)
    motor_b(0)
    print("Stopped for 2 seconds...")
    print_voltages()  # Final voltage check
    print()
    time.sleep(2)
    
    cycle += 1
