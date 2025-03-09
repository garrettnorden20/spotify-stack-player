import keyboard

def on_key(event):
    print(f"Key: {event.name}, Scan Code: {event.scan_code}, Event Type: {event.event_type}")

# Hook into keyboard events
keyboard.hook(on_key)

# Keep the script running
print("Listening for keyboard inputs... Press 'esc' to exit.")
keyboard.wait('esc')  # Stops the script when 'esc' is pressed