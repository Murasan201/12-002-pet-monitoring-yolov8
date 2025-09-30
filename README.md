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

### Test the System

Before running the full monitoring system, test each component:

```bash
python3 main.py
```

The system will automatically run component tests on startup:
- Slack connection
- Camera functionality
- Servo operation

### Run Monitoring System

Start the monitoring system:

```bash
python3 main.py
```

The system will:
1. Run an immediate monitoring cycle
2. Schedule subsequent cycles every 10 minutes (configurable)
3. Log all activities to `pet_monitoring.log` and console

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

### Camera Settings
- `CAMERA_INDEX`: Camera device index (default: 0)
- `FRAME_WIDTH`: Camera frame width (default: 640)
- `FRAME_HEIGHT`: Camera frame height (default: 480)

### Control Parameters
- `KP_PAN`: Proportional gain for pan control (default: 0.02)
- `KP_TILT`: Proportional gain for tilt control (default: 0.02)
- `DEADBAND`: Deadband in pixels to prevent jitter (default: 10)

### Scanning & Tracking
- `SCAN_STEPS_PAN`: Number of pan positions during scan (default: 9)
- `SCAN_STEPS_TILT`: Number of tilt positions during scan (default: 5)
- `TRACKING_DURATION`: Duration to track pet in seconds (default: 8.0)

### Image Settings
- `IMAGE_SAVE_DIR`: Directory for captured images (default: ./captured_images)
- `CAPTURE_COUNT`: Number of images to capture (default: 3)
- `IMAGE_LONG_EDGE`: Target size for long edge in pixels (default: 800)
- `JPEG_QUALITY`: JPEG compression quality 0-100 (default: 70)

### Schedule
- `SCHEDULE_INTERVAL`: Minutes between monitoring cycles (default: 10)

## Project Structure

```
12-002-pet-monitoring-yolov8/
├── camera_tracker.py          # Camera tracking and image capture module
├── slack_uploader.py          # Slack integration module
├── main.py                    # Main orchestrator
├── requirements.txt           # Python dependencies
├── .env.example              # Example environment configuration
├── pet_monitoring_requirements.md  # Requirements document (Japanese)
├── raspberry_pi_5_pan_tilt_追跡制御_検討レポート（pca_9685_＋p制御）rev_4.md  # Technical report (Japanese)
└── README.md                 # This file
```

## Module Overview

### camera_tracker.py
Handles all camera-related operations:
- Pan-tilt servo initialization and control
- Full area scanning for pet detection
- P-control based tracking
- Image capture with automatic resizing and compression

### slack_uploader.py
Manages Slack communication:
- File upload using Slack Web API (`files_upload_v2`)
- Message posting
- Connection testing

### main.py
Main orchestrator that:
- Loads configuration from `.env`
- Schedules periodic monitoring cycles
- Coordinates scanning, tracking, and notification
- Handles error recovery and logging

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