# Pet Monitoring System with YOLOv8

An automated pet monitoring system using Raspberry Pi, Camera Module, and YOLOv8 for intelligent pet detection and tracking. The system automatically adjusts the camera angle to keep your pet centered in the frame and sends notifications to Slack with captured images.

## Features

- 🐾 **Intelligent Pet Detection**: Uses YOLOv8 to detect dogs and cats
- 📷 **Auto-Tracking**: Pan-tilt camera automatically follows detected pets using P-control
- 🔍 **Full Area Scanning**: Systematically scans the entire field of view
- 📸 **Image Capture**: Captures 3 optimized JPEG images when pets are detected
- 💬 **Slack Notifications**: Sends captured images to Slack channel
- ⏰ **Scheduled Operation**: Runs monitoring cycles every 10 minutes (configurable)
- 🎯 **Jitter-Free Control**: Hardware PWM generation using PCA9685 servo driver

## Hardware Requirements

- **Raspberry Pi 5** (recommended) or Raspberry Pi 4
- **Camera Module v3** or compatible USB camera
- **PCA9685 16-Channel PWM/Servo HAT** ([Adafruit #2327](https://www.adafruit.com/product/2327))
- **SG90 Servo Motors × 2** (for pan and tilt control)
- **Pan-Tilt Bracket** (for camera and servo mounting)
- **External 5V Power Supply** (2A or higher for servos)

## Software Requirements

- Raspberry Pi OS (64-bit)
- Python 3.8 or higher

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Murasan201/12-002-pet-monitoring-yolov8.git
cd 12-002-pet-monitoring-yolov8
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Download YOLOv8 Model

The system will automatically download the YOLOv8n model on first run, or you can manually download it:

```bash
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### 4. Configure Environment

Copy the example environment file and edit it with your settings:

```bash
cp .env.example .env
nano .env
```

Required configuration:
- `SLACK_BOT_TOKEN`: Your Slack Bot User OAuth Token
- `SLACK_CHANNEL`: Target Slack channel (e.g., `#pet-monitoring`)

### 5. Set Up Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or use an existing one
3. Add the following OAuth scopes under "OAuth & Permissions":
   - `chat:write`
   - `files:write`
4. Install the app to your workspace
5. Copy the "Bot User OAuth Token" to your `.env` file

## Hardware Setup

### Wiring Diagram

| Component | Connection |
|-----------|------------|
| HAT VCC | Raspberry Pi 3.3V |
| HAT GND & Servo GND | Raspberry Pi GND (common ground) |
| SDA/SCL | Pi GPIO2 (SDA) / GPIO3 (SCL) |
| V+ (Servo Power) | External 5V Power Supply (2A+) |
| Channel 0 | Pan Servo (SG90) |
| Channel 1 | Tilt Servo (SG90) |

**Important**: Keep servo power supply separate from Raspberry Pi power to prevent voltage drops.

## Usage

### Run Camera Tracker (Standalone)

Test the camera tracking system with the `camera_tracker.py` script:

```bash
# Basic execution (default: detect cats and dogs, track for 8 seconds)
python3 camera_tracker.py

# Display video while running
python3 camera_tracker.py --display

# Continuous mode (press Ctrl+C or 'q' to stop)
python3 camera_tracker.py --display --continuous
```

### Changing Detection Target

By default, the system detects **cats** and **dogs**. You can change this via command line:

```bash
# List all available class names
python3 camera_tracker.py --list-classes

# Detect only person
python3 camera_tracker.py --classes person

# Detect person, cat, and dog
python3 camera_tracker.py --classes person cat dog
```

### Command Line Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--model` | str | `models/yolov8s_h8l.hef` | HEF model file path |
| `--classes` | str (multiple) | `cat dog` | Target class names (space-separated) |
| `--list-classes` | flag | - | Show available class names and exit |
| `--width` | int | `640` | Camera image width (pixels) |
| `--height` | int | `480` | Camera image height (pixels) |
| `--flip` | flag | - | Flip camera image vertically |
| `--kp-pan` | float | `0.01` | Proportional gain for pan control |
| `--kp-tilt` | float | `0.01` | Proportional gain for tilt control |
| `--deadband` | int | `40` | Deadband in pixels |
| `--delta-max` | float | `1.0` | Max angle change per update (degrees) |
| `--scan-pan` | int | `9` | Pan axis scan steps |
| `--scan-tilt` | int | `5` | Tilt axis scan steps |
| `--duration` | float | `8.0` | Tracking duration (seconds) |
| `--fps` | float | `5.0` | Tracking loop update frequency (Hz) |
| `--continuous` | flag | - | Continuous mode (Ctrl+C or 'q' to exit) |
| `--display` | flag | - | Display camera video in window |
| `--log` | str | None | Debug log CSV file path |
| `--capture` | flag | - | Capture images after tracking |
| `--capture-dir` | str | `captures` | Capture save directory |
| `--capture-count` | int | `3` | Number of images to capture |

### Usage Examples

```bash
# Adjust P-control parameters (faster response)
python3 camera_tracker.py --kp-pan 0.02 --kp-tilt 0.02 --deadband 20

# Output debug log
python3 camera_tracker.py --log tracking.csv --display

# Capture images after tracking
python3 camera_tracker.py --capture --capture-dir ./images --capture-count 5

# For upside-down mounted camera
python3 camera_tracker.py --flip

# High resolution
python3 camera_tracker.py --width 1280 --height 720
```

### Run Full Monitoring System

Start the full monitoring system with Slack notifications:

```bash
# Basic execution (1-hour interval for Slack notifications)
python3 main.py

# Set notification interval to 30 minutes
python3 main.py --interval 30

# Disable Slack notifications (test mode)
python3 main.py --no-slack

# Display camera feed
python3 main.py --display

# Verbose logging
python3 main.py --verbose
```

The system will:
1. Continuously track pets in real-time using P-control
2. Periodically capture images (default: 1 hour)
3. Send captured images to Slack at specified intervals (default: 1 hour)
4. Log all activities to console

### Run as a Service (Optional)

To run the system automatically on boot, create a systemd service:

```bash
sudo nano /etc/systemd/system/pet-monitoring.service
```

Add the following content (adjust paths as needed):

```ini
[Unit]
Description=Pet Monitoring System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/12-002-pet-monitoring-yolov8
ExecStart=/usr/bin/python3 /home/pi/12-002-pet-monitoring-yolov8/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable pet-monitoring.service
sudo systemctl start pet-monitoring.service
sudo systemctl status pet-monitoring.service
```

## Configuration

All configuration is done via the `.env` file. Key parameters:

### Slack Settings
- `SLACK_BOT_TOKEN`: Bot OAuth token
- `SLACK_CHANNEL`: Target channel for notifications
- `SLACK_NOTIFICATION_INTERVAL`: Slack notification interval in minutes (default: 60)

### Camera Settings
- `CAMERA_INDEX`: Camera device index (default: 0)
- `FRAME_WIDTH`: Camera frame width (default: 640)
- `FRAME_HEIGHT`: Camera frame height (default: 480)
- `CAMERA_FLIP_VERTICAL`: Flip camera vertically (true/false, default: true)

### Control Parameters
- `KP_PAN`: Proportional gain for pan control (default: 0.01)
- `KP_TILT`: Proportional gain for tilt control (default: 0.01)
- `DEADBAND`: Deadband in pixels to prevent jitter (default: 40)

### Scanning & Tracking
- `SCAN_STEPS_PAN`: Number of pan positions during scan (default: 9)
- `SCAN_STEPS_TILT`: Number of tilt positions during scan (default: 5)
- `TRACKING_DURATION`: Duration to track pet in seconds (default: 8.0)

### Image Settings
- `IMAGE_SAVE_DIR`: Directory for captured images (default: ./captured_images)
- `IMAGE_CAPTURE_INTERVAL`: Image capture interval in minutes (default: 60)
- `IMAGE_LONG_EDGE`: Target size for long edge in pixels (default: 800)
- `JPEG_QUALITY`: JPEG compression quality 0-100 (default: 70)

## Project Structure

```
12-002-pet-monitoring-yolov8/
├── camera_tracker.py          # Camera tracking and image capture module
├── slack_notifier.py          # Slack notification module
├── main.py                    # Main orchestrator (continuous tracking + periodic notification)
├── servo_control.py           # Servo control library
├── raspi_hailo8l_yolo.py     # Hailo-8L YOLO detector library
├── requirements.txt           # Python dependencies
├── .env.example              # Example environment configuration
├── docs/                      # Documentation directory
│   ├── README.md              # Documentation index
│   ├── pet_monitoring_requirements.md  # Requirements (Japanese)
│   ├── servo_control_specification.md  # Servo control spec
│   ├── detection_and_tracking_specification.md  # Detection/tracking spec
│   ├── slack_notification_specification.md  # Slack notification spec
│   └── ...                    # Other technical documents
└── README.md                  # This file
```

## Module Overview

### camera_tracker.py
Handles all camera-related operations:
- Pan-tilt servo initialization and control
- Full area scanning for pet detection
- P-control based tracking
- Image capture with automatic resizing and compression
- Public API: `scan_and_track()`, `capture_images()`, `get_latest_image()`

### slack_notifier.py
Manages Slack communication:
- Image upload using Slack Web API (`files_upload_v2`)
- Text message posting
- Configuration validation
- Public API: `upload_images()`, `send_message()`, `validate_config()`

### main.py
Main orchestrator that:
- Continuously tracks pets in real-time
- Periodically captures images at specified intervals
- Sends captured images to Slack on schedule
- Handles error recovery and graceful shutdown (Ctrl+C)

## Control Algorithm

The system uses a simple **P-control (Proportional Control)** algorithm for tracking:

1. **Error Calculation**: Compute difference between detected pet center and frame center
2. **Proportional Update**: `Δangle = -Kp × error`
3. **Angle Limiting**: Clamp angles to valid servo range [0°, 180°]
4. **Deadband**: Ignore small errors to prevent micro-jitter

This approach provides stable tracking without the complexity of PID control, suitable for the low-frequency updates required by this application.

## Troubleshooting

### Camera not detected
```bash
# List video devices
ls -l /dev/video*

# Test camera
raspistill -o test.jpg  # For Camera Module
```

### I2C issues
```bash
# Enable I2C
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable

# Check I2C devices
sudo i2cdetect -y 1
```

### Slack upload fails
- Verify your bot token is correct
- Ensure the bot is added to the target channel
- Check bot has required scopes: `chat:write`, `files:write`

### Servos not moving
- Check external 5V power supply is connected
- Verify common ground between Pi and servo power
- Test servo channels are 0 and 1 (pan and tilt)

## Related Projects

- [12-001-pan-tilt-pet-tracker](https://github.com/Murasan201/12-001-pan-tilt-pet-tracker) - Servo control reference implementation

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- YOLOv8 by [Ultralytics](https://github.com/ultralytics/ultralytics)
- Control algorithm inspired by [SunFounder PiCar-X](https://docs.sunfounder.com/projects/picar-x/ja/latest/python/python_stare_at_you.html)
- Servo control using [Adafruit CircuitPython](https://github.com/adafruit/Adafruit_CircuitPython_ServoKit)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please use the [GitHub Issues](https://github.com/Murasan201/12-002-pet-monitoring-yolov8/issues) page.