# Claude Code Rules

## Project Overview
This is a pet monitoring system using YOLOv8 for object detection.

**Repository**: https://github.com/Murasan201/12-002-pet-monitoring-yolov8

**Requirements Document**: `pet_monitoring_requirements.md`

## Work Process
- **IMPORTANT**: Always review `pet_monitoring_requirements.md` before starting any work
- Ensure all implementations align with the requirements specified in the document

## Coding Guidelines
- Follow Python PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and modular
- **Comments**: Write all code comments in Japanese
- **Comment Style**: Add beginner-friendly comments without compromising readability

## Git Commit Guidelines
- Write clear, concise commit messages
- Use present tense (e.g., "Add feature" not "Added feature")
- Reference issue numbers when applicable

## Testing
- Write unit tests for new functionality
- Ensure all tests pass before committing
- Maintain test coverage

## Documentation
- **Documentation Directory**: All project documentation, specifications, and design documents must be stored in the `docs/` directory
- **File Organization**:
  - Specifications: `docs/*_specification.md`
  - Design documents: `docs/*_design.md`
  - Implementation notes: `docs/*_notes.md`
- Update documentation when adding new features
- Include usage examples where appropriate
- Keep README.md up to date
- Write documentation in markdown format

## MCP Tools Usage
- **Web Search**: Use Google Search agent (MCP) when you need to search for information online
- **Code Understanding**: Use Serena (MCP) for analyzing and understanding documentation and source code structure when needed

## Camera Mount Control
This project uses a pan-tilt camera mount controlled by servo motors.

**Control Library**: `servo_control.py` (copied from 12-001-rpi-pan-tilt-camera-mount)

**Reference Repository**: https://github.com/Murasan201/12-001-rpi-pan-tilt-camera-mount
- Local reference: `/home/pi/work/project/kodansya/12-002-pet-monitoring-yolov8/reference/12-001-rpi-pan-tilt-camera-mount`

### Hardware Configuration
- **Servo Driver**: Adafruit 16-Channel PWM/Servo HAT (PCA9685)
- **Servo Motors**: SG90 x 2
- **Pan Servo**: Channel 0 (35-125°, center at 80°)
- **Tilt Servo**: Channel 1 (45-135°, center at 90°)
- **Communication**: I2C (address 0x40)
- **PWM Frequency**: 50Hz
- **Pulse Width**: 750-2250μs (SG90 optimized)

### Available Functions
The `servo_control.py` library provides the following functions for camera control:

```python
import servo_control

# Initialize servo kit
kit = servo_control.initialize_servo_kit()

# Move pan servo (horizontal: left/right)
servo_control.set_pan_angle(kit, 80)

# Move tilt servo (vertical: up/down)
servo_control.set_tilt_angle(kit, 90)

# Move both servos simultaneously
servo_control.set_pan_tilt(kit, 80, 90)

# Return to center position
servo_control.set_center_position(kit)

# Release servos (stop holding position)
servo_control.release_servos(kit)
```

### Key Features
- **Trapezoidal Control**: Smooth motion with automatic deceleration near target
- **Vibration Prevention**: Optimized pulse width settings for SG90 servos
- **Library Design**: Reusable functions for integration with object tracking
- **Validated Range**: Tested safe operating ranges for the physical mount

### Related Documentation
- Specification: `reference/12-001-rpi-pan-tilt-camera-mount/docs/specification.md`
- Troubleshooting: `reference/12-001-rpi-pan-tilt-camera-mount/docs/troubleshooting.md`
- README: `reference/12-001-rpi-pan-tilt-camera-mount/README.md`