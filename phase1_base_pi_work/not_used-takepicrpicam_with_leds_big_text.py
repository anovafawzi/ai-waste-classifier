import time
import numpy as np
from picamera2 import Picamera2
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image, ImageDraw, ImageFont
from threading import Thread
from gpiozero import Button, OutputDevice, LED
from signal import pause
import random
import textwrap

# Luma.core.render is needed for the canvas function
from luma.core.render import canvas
# Luma.core.legacy is needed for the text function and font
from luma.core.legacy import text
from luma.core.legacy.font import proportional, LCD_FONT

# -----------------------------------------------------------------------------
# Global Variables and Configuration
# -----------------------------------------------------------------------------
picam2 = None
camera_running = False
main_loop_thread = None
led_thread = None

# Define the physical GPIO pins for the buttons.
# We are now using gpiozero, which simplifies button handling.
# Button 1 will be for starting/stopping the camera feed.
START_BUTTON_PIN = 16
# Button 2 will be for capturing a photo.
CAPTURE_BUTTON_PIN = 26

# LED pins
RED_LED_PIN = 22
YELLOW_LED_PIN = 27
GREEN_LED_PIN = 17
BLUE_LED_PIN = 6

# -----------------------------------------------------------------------------
# Backlight and Display Setup
# -----------------------------------------------------------------------------
# Based on the pins you provided:
# SCLK -> GPIO11 (SPI CLOCK)
# MOSI -> GPIO10 (SPI DATA)
# DC   -> GPIO25 (Data/Command)
# RST  -> GPIO24 (Reset)
# CS   -> GPIO8  (Chip Select)
# BLK  -> GPIO23 (Backlight)

# Control the backlight pin using a gpiozero OutputDevice.
backlight = OutputDevice(23, active_high=True, initial_value=True)

# Luma.LCD requires a serial interface object.
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=24)

# Initialize the ST7789 device with the correct dimensions.
device = st7789(serial, width=320, height=240, rotate=0, bgr=False)

# -----------------------------------------------------------------------------
# GPIO Button and LED Setup
# -----------------------------------------------------------------------------
# Set up the buttons. gpiozero handles pull-up/pull-down resistors
# and event detection automatically.
start_button = Button(START_BUTTON_PIN) # Assumes button is connected to GND
capture_button = Button(CAPTURE_BUTTON_PIN)

# Set up the LEDs
red_led = LED(RED_LED_PIN)
yellow_led = LED(YELLOW_LED_PIN)
green_led = LED(GREEN_LED_PIN)
blue_led = LED(BLUE_LED_PIN)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def turn_off_all_leds():
    """Turn off all LEDs"""
    red_led.off()
    yellow_led.off()
    green_led.off()
    blue_led.off()

def display_centered_message(message, duration=3):
    """Display a centered message on the screen with bigger text that can span multiple lines"""
    # Create a blank image to draw the message on
    message_image = Image.new('RGB', (device.width, device.height), "black")
    draw = ImageDraw.Draw(message_image)

    # Load a larger font for drawing the text
    try:
        # Try to use a system font with larger size
        font = ImageFont.truetype("arial.ttf", 32)
    except IOError:
        try:
            # Try alternative font names
            font = ImageFont.truetype("DejaVuSans.ttf", 32)
        except IOError:
            try:
                # Try another common font
                font = ImageFont.truetype("LiberationSans-Regular.ttf", 32)
            except IOError:
                # Fall back to default font (will be smaller)
                font = ImageFont.load_default()

    # Wrap text to fit the screen width
    # Estimate characters per line based on screen width and font size
    chars_per_line = device.width // 16  # Rough estimate for 32pt font
    wrapped_lines = textwrap.wrap(message, width=chars_per_line)
    
    # If wrapping results in too many lines, try with smaller font
    if len(wrapped_lines) > 6:  # Too many lines for screen
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", 24)
            except IOError:
                font = ImageFont.load_default()
        
        chars_per_line = device.width // 12  # Adjust for smaller font
        wrapped_lines = textwrap.wrap(message, width=chars_per_line)

    # Calculate total text height
    line_height = 0
    for line in wrapped_lines:
        text_bbox = draw.textbbox((0, 0), line, font=font)
        line_height = max(line_height, text_bbox[3] - text_bbox[1])
    
    total_text_height = len(wrapped_lines) * line_height
    
    # Calculate starting Y position to center all lines vertically
    start_y = (device.height - total_text_height) // 2
    
    # Draw each line centered horizontally
    current_y = start_y
    for line in wrapped_lines:
        # Get the dimensions of the current line
        text_bbox = draw.textbbox((0, 0), line, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        
        # Calculate the position to draw the text for horizontal centering
        x_pos = (device.width - text_width) // 2
        
        # Draw the text on the image
        draw.text((x_pos, current_y), line, fill="white", font=font)
        
        # Move to next line
        current_y += line_height
    
    # Display the message on the screen
    device.display(message_image)
    
    # Pause for the specified duration
    time.sleep(duration)

# -----------------------------------------------------------------------------
# Core Functions
# -----------------------------------------------------------------------------
def camera_feed_loop():
    """
    Function to run in a separate thread for the camera feed.
    """
    global picam2, camera_running
    
    try:
        # Initialize the Picamera2 object.
        picam2 = Picamera2()

        # Configure the camera to capture a 320x240 image.
        camera_config = picam2.create_preview_configuration(main={"size": (320, 240), "format": "XRGB8888"})
        picam2.configure(camera_config)

        # Start the camera stream.
        picam2.start()

        print("Camera feed started.")
        camera_running = True

        while camera_running:
            # Capture a frame as a Pillow Image.
            frame_image = picam2.capture_image()
            
            # Display the image on the LCD.
            device.display(frame_image)
            
            # A short delay to control the frame rate.
            time.sleep(0.05)
    except RuntimeError as e:
        print(f"Error: {e}. Check your camera connection and configuration.")
        # Stop the loop and reset camera_running state
        camera_running = False
    except Exception as e:
        print(f"Camera loop error: {e}")
    finally:
        if picam2:
            picam2.stop()
            # Explicitly close the camera resource to ensure it's fully released.
            picam2.close()
            print("Camera feed stopped and resource closed.")
        picam2 = None

def start_camera_on_press():
    """
    Callback function to start the camera feed when the button is pressed.
    This function is triggered by the gpiozero event.
    """
    global main_loop_thread, camera_running

    if not camera_running or camera_running == "processing":
        print(f"Start button pressed on GPIO {START_BUTTON_PIN}. Starting camera feed...")
        
        # Turn off all LEDs immediately when starting camera
        turn_off_all_leds()
        
        # Display startup message for 3 seconds with bigger text
        display_centered_message("Camera Starting! Take a picture of your waste with the capture button", 3)
        
        # Start the camera loop in a new thread.
        main_loop_thread = Thread(target=camera_feed_loop)
        main_loop_thread.daemon = True # Allows the thread to exit with the main program
        main_loop_thread.start()
    else:
        print(f"Start button pressed on GPIO {START_BUTTON_PIN}. Camera is already running. Stopping it...")
        camera_running = False
        
        # Turn off all LEDs when stopping camera
        turn_off_all_leds()
        
        # Wait for the camera thread to finish completely before clearing the screen.
        if main_loop_thread and main_loop_thread.is_alive():
            main_loop_thread.join()
        
        device.clear()


def simulate_api_call():
    """Simulate API call for waste classification"""
    # TODO: Replace this with actual API call
    time.sleep(3)  # Simulate processing time
    # Simulate a random waste type number between 1 and 4.
    result_number = random.randint(1, 4)
    results = {
        1: "Rubbish",
        2: "Recyclable",
        3: "Organics",
        4: "Ecowaste"
    }
    result_name = results.get(result_number, "Unknown")
    return result_name, result_number

def blink_leds_during_processing():
    """Blink LEDs in sequence during API processing"""
    leds = [blue_led, red_led, yellow_led, green_led]
    led_index = 0
    
    while camera_running == "processing":
        # Turn off all LEDs
        turn_off_all_leds()
        # Turn on current LED
        leds[led_index].on()
        time.sleep(0.3)
        # Move to next LED
        led_index = (led_index + 1) % len(leds)
        
def turn_on_led_by_waste_type(wastetype):
    """
    Turns on a specific LED based on the waste type number.

    Args:
        wastetype (int): The waste type number (1 for red, 2 for yellow, etc.).
                         1: Rubbish (Red)
                         2: Recyclable (Yellow)
                         3: Organics (Green)
                         4: Ecowaste (Blue)
    """
    # First, turn off all LEDs to ensure only one is lit at a time.
    turn_off_all_leds()

    # Check the waste type number and turn on the corresponding LED.
    if wastetype == 1:
        print("Activating Red LED for Rubbish.")
        red_led.on()
    elif wastetype == 2:
        print("Activating Yellow LED for Recyclable.")
        yellow_led.on()
    elif wastetype == 3:
        print("Activating Green LED for Organics.")
        green_led.on()
    elif wastetype == 4:
        print("Activating Blue LED for Ecowaste.")
        blue_led.on()
    else:
        print(f"Warning: Unknown waste type number: {wastetype}. No LED will be turned on.")

def capture_and_save_on_press():
    """
    Callback function to take a single picture and save it.
    This function is triggered by the gpiozero event.
    """
    global picam2, camera_running, led_thread
    if picam2 and camera_running:
        try:
            print(f"Capture button pressed on GPIO {CAPTURE_BUTTON_PIN}. Capturing image...")
            
            # Capture a high-resolution still image from the running preview.
            filename = f"image_{int(time.time())}.jpg"
            picam2.capture_file(filename)
            print(f"Image saved as {filename}")

            # Stop the camera feed now that the capture is complete.
            camera_running = False
            if main_loop_thread and main_loop_thread.is_alive():
                main_loop_thread.join()

            # Display processing message
            display_centered_message("Image captured, classifying waste...", 1)
            
            # Set processing state and start LED blinking
            camera_running = "processing"
            led_thread = Thread(target=blink_leds_during_processing)
            led_thread.daemon = True
            led_thread.start()
            
            try:
                # Simulate API call (replace with actual API call)
                result_name, result_number = simulate_api_call()
                
                # Stop LED blinking and wait for thread to finish
                camera_running = False
                if led_thread and led_thread.is_alive():
                    led_thread.join(timeout=1)
                
                # Now that the result is back, turn on the correct LED
                turn_on_led_by_waste_type(result_number)
                
                # Display success message
                display_centered_message(f"Classification complete! {result_name}. Press start to classify another item", 5)
                
            except Exception as api_error:
                # Stop LED blinking and wait for thread to finish
                camera_running = False
                if led_thread and led_thread.is_alive():
                    led_thread.join(timeout=1)
                turn_off_all_leds()
                
                # Display error message
                display_centered_message("Classification failed. Press start to try again", 3)
                print(f"API call failed: {api_error}")
            
        except Exception as e:
            camera_running = False
            turn_off_all_leds()
            print(f"Failed to capture image: {e}")
    else:
        print(f"Capture button pressed on GPIO {CAPTURE_BUTTON_PIN}. Cannot capture. Camera is not running.")
        
# -----------------------------------------------------------------------------
# Main Program
# -----------------------------------------------------------------------------
print("Program is starting...")

# Ensure all LEDs are off at startup
turn_off_all_leds()

# Add event detection for the buttons using gpiozero's 'when_pressed' handler.
start_button.when_pressed = start_camera_on_press
capture_button.when_pressed = capture_and_save_on_press

print("Ready. Press the start button to begin the camera feed.")
print("Press the capture button to take a photo.")
print("Press Ctrl+C to exit.")

# The 'pause()' function keeps the program running and listening for events.
try:
    pause()
except KeyboardInterrupt:
    print("\nProgram stopped.")
    # Turn off all LEDs when exiting
    turn_off_all_leds()
