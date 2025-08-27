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
    """Display a centered message on the screen for a specified duration"""
    # Create a blank image to draw the message on
    message_image = Image.new('RGB', (device.width, device.height), "black")
    draw = ImageDraw.Draw(message_image)

    # Load a Pillow font for drawing the text
    try:
        # Use a system font if available, otherwise fall back to the default
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    # Get the dimensions of the text to be drawn using the selected font
    text_bbox = draw.textbbox((0, 0), message, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Calculate the position to draw the text for perfect centering
    x_pos = (device.width - text_width) // 2
    y_pos = (device.height - text_height) // 2

    # Draw the text on the image
    draw.text((x_pos, y_pos), message, fill="white", font=font)
    
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

    if not camera_running:
        print(f"Start button pressed on GPIO {START_BUTTON_PIN}. Starting camera feed...")
        
        # Turn off all LEDs immediately when starting camera
        turn_off_all_leds()
        
        # Display startup message for 3 seconds
        display_centered_message("Turning on camera, take a picture of your waste with blue button...", 3)
        
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


def capture_and_save_on_press():
    """
    Callback function to take a single picture and save it.
    This function is triggered by the gpiozero event.
    """
    global picam2
    if picam2 and camera_running:
        try:
            print(f"Capture button pressed on GPIO {CAPTURE_BUTTON_PIN}. Capturing image...")
            # Capture a high-resolution still image.
            filename = f"image_{int(time.time())}.jpg"
            picam2.capture_file(filename)
            print(f"Image saved as {filename}")

            # Display confirmation message for 2 seconds
            display_centered_message("Waste captured!", 2)
            
            # Randomly select and turn on one LED for 3 seconds
            leds = [red_led, yellow_led, green_led, blue_led]
            selected_led = random.choice(leds)
            selected_led.on()
            
            # Keep the LED on for 3 seconds (unless camera is restarted)
            led_start_time = time.time()
            while time.time() - led_start_time < 3:
                if not camera_running:  # If camera is stopped, turn off LED immediately
                    selected_led.off()
                    break
                time.sleep(0.1)  # Small delay to check camera status frequently
            else:
                # Turn off the LED after 3 seconds if camera is still running
                selected_led.off()
            
        except Exception as e:
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