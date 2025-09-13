# settings.py
"""
Global game settings and constants for the NeuroGrip Maze Game.
"""

# =============================================================================
#  1. MASTER GAME SETTINGS
# =============================================================================

# Change this single variable to switch gameplay styles
CONTROL_MODE = "PROPORTIONAL"  # Options: "PROPORTIONAL", "CONSTANT_MOTION"

# =============================================================================
#  2. GAMEPLAY AND PHYSICS CONSTANTS
# =============================================================================
TILE_SIZE = 40

# --- Settings for PROPORTIONAL Mode (Start/Stop Controls) ---
PLAYER_SPEED = 260         # Increased from 250 for quicker movement
PLAYER_ACCELERATION = 0.1       # Lower value = smoother/slower acceleration
PLAYER_BOUNCINESS = 0.4         # NEW: How much velocity is retained after hitting a wall

# --- Settings for CONSTANT_MOTION Mode (Steering Controls) ---
CONSTANT_BALL_SPEED = 150
ROTATION_SPEED = 200

# =============================================================================
#  3. HARDWARE SETTINGS
# =============================================================================
SERIAL_PORT = "COM5"            # ⚠️ Change to your ESP32's COM port
TILT_SENSITIVITY = 5000.0       # Lower = more sensitive tilt control
MAX_TILT_VALUE = 20000.0        # Maximum expected tilt value
FSR_THRESHOLD = 500             # The ADC value from an FSR needed to register a "grip"
MAX_FSR_VALUE = 4095.0          # The ADC value corresponding to maximum grip

# =============================================================================
#  4. DISPLAY AND COLOR CONSTANTS
# =============================================================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (10, 60, 225)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BUTTON_BG_COLOR = (70, 70, 150)
BUTTON_SHADOW_COLOR = (40, 40, 90) # NEW: Added for button depth
BARRIER_COLOR = (180, 0, 0)

# =============================================================================
#  5. HUD (TIMER AND GRIP METER) SETTINGS
# =============================================================================
HUD_FONT_SIZE = 36
TIMER_POS = (10, 10)
GRIP_METER_POS = (140, 12)
GRIP_METER_SIZE = (200, 20) # Width, Height
GRIP_METER_BG_COLOR = (50, 50, 50)
GRIP_METER_FILL_COLOR = YELLOW
GRIP_METER_THRESHOLD_COLOR = RED

# =============================================================================
#  6. LEVEL DEFINITIONS
# =============================================================================
# W = Wall, ' ' = Empty, P = Player Start, H = Hole
LEVELS = {
    "Easy": [
        "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
        "W P                          W",
        "W                            W",
        "W  WWWWWWWWWWWWWWWWWWWWWWWW  W",
        "W                            W",
        "W                            W",
        "W                            W",
        "W  WWWWWWWWWWWWWWWWWWWWWWWW  W",
        "W                            W",
        "W                            W",
        "W                            H",
        "W  WWWWWWWWWWWWWWWWWWWWWWWW  W",
        "W                            W",
        "W                            W",
        "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    ],
    "Medium": [
        "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
        "W P  W                     H W",
        "W    W WWW WWWWWWWWWWWW WWWW W",
        "W WWWW     W          W      W",
        "W W    WWWWW WWWWWWWW W WWWW W",
        "W WWWW W   W W      W W W  W W",
        "W W    W W W W WWWW W W WW W W",
        "W W WWWW W W W W  W W W    W W",
        "W W      W   W WWWW W WWWWWW W",
        "W WWWWWWWWWWWW W    W        W",
        "W            W WWWWWWWWWWWWW W",
        "W WWWWWWWWWW W               W",
        "W          W WWWWWWWWWWWWWWW W",
        "W WWWWWWWW W                 W",
        "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    ],
  "Hard": [
        "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
        "WP W   W   W W   W     W   H W",
        "W  W W W WWW W W W WWWWW WWW W",
        "WW W W W W   W W W W     W   W",
        "W  W W W W WWW W W W WWWWW WWW W",
        "W WW W W W W   W W   W     W",
        "W W  W W W W WWWWWWWWW WWW W W",
        "W W WWW W  W  W   W W   W    W",
        "W W W   WWWWWWW W W W W WWWWW W",
        "W W W WWWW    W W W W W W     W",
        "W W W W   WWWWW W W W W W WWWWW",
        "W W W   W W     W W W W     W",
        "W W W WWW W WWWWWWWWW WWWWWW  W",
        "W     W                     W",
        "WWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",
    ]
}


# Screen dimensions are calculated automatically from the 'Easy' level layout
SCREEN_WIDTH = len(LEVELS["Easy"][0]) * TILE_SIZE
SCREEN_HEIGHT = len(LEVELS["Easy"]) * TILE_SIZE