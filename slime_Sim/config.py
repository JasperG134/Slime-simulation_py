# config.py
"""
A single config.py file containing TEN different presets for a GPU-based slime simulation.

Set CURRENT_PRESET = 1..10 to pick which preset's parameters to use.

Feel free to tweak or add more presets. The code reading these config values
should just do something like:

from config import *

Then use them in the main GPU slime code.

Presets #1..#4 attempt to roughly replicate those 'bubble/cell', 'blue net',
'green lumps', and 'wrinkled lines' screenshots, while #5..#10 are additional
interesting variants.
"""

CURRENT_PRESET = 4 # Choose any from 1..10

# We'll store all presets in a dictionary of dictionaries:
ALL_PRESETS = {

    #---------------------------------------------------------
    # 1) A fast moving chaotic setting
    #---------------------------------------------------------
    1: dict(
        WINDOW_WIDTH  = 1280,
        WINDOW_HEIGHT = 720,
        SIM_WIDTH  = 1024,
        SIM_HEIGHT = 1024,

        MULTI_SPECIES = False,
        NUM_SPECIES   = 1,

        NUM_AGENTS     = 1_000_000,  # Big population
        AGENT_SPEED    = 5,
        TURN_SPEED     = 0.2,
        SENSOR_ANGLE_DEG = 30.0,
        SENSOR_DISTANCE  = 7.0,

        # Keep deposit moderate, but rely on blur to inflate "cells"
        DEPOSIT_AMOUNT     = 0.15,
        AGENT_DEPOSIT_SCALE= 250_000,  # scales deposit based on total agent count

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.01,

        EVAPORATION_FACTOR = 0.92,  # fade slower -> stronger "walls"
        BLUR_RADIUS        = 1,     # bigger blur => bubble walls
        BLUR_PASSES        = 1,     # 2 passes each frame

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        COLOR_MODE       = "SUM",   # sum channels => white
        COLOR_MULTIPLIER = 60.0,    # fairly high brightness
        BACKGROUND_COLOR = (0.0, 0.0, 0.0, 1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset1_screenshot.png"
    ),

    #---------------------------------------------------------
    # 2) "White Net" pattern
    #---------------------------------------------------------
    2: dict(
        WINDOW_WIDTH  = 1280,
        WINDOW_HEIGHT = 720,
        SIM_WIDTH  = 1024,
        SIM_HEIGHT = 1024,

        MULTI_SPECIES = False,
        NUM_SPECIES   = 1,

        NUM_AGENTS     = 1_000_000,  # Big population
        AGENT_SPEED    = 5,
        TURN_SPEED     = 0.4,
        SENSOR_ANGLE_DEG = 30.0,
        SENSOR_DISTANCE  = 100.0,

        # Keep deposit moderate, but rely on blur to inflate "cells"
        DEPOSIT_AMOUNT     = 0.05,
        AGENT_DEPOSIT_SCALE= 1_000_000,  # scales deposit based on total agent count

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.01,

        EVAPORATION_FACTOR = 0.92,  # fade slower -> stronger "walls"
        BLUR_RADIUS        = 1,     # bigger blur => bubble walls
        BLUR_PASSES        = 1,     # 2 passes each frame

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        COLOR_MODE       = "SUM",   # sum channels => white
        COLOR_MULTIPLIER = 60.0,    # fairly high brightness
        BACKGROUND_COLOR = (0.0, 0.0, 0.0, 1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset1_screenshot.png"
    ),

    #---------------------------------------------------------
    # 3) "Green Dots" pattern
    #---------------------------------------------------------
    3: dict(
        WINDOW_WIDTH=1280,
        WINDOW_HEIGHT=720,
        SIM_WIDTH=1024,
        SIM_HEIGHT=1024,

        MULTI_SPECIES=False,
        NUM_SPECIES=1,

        NUM_AGENTS=1_000_000,  # REAL Big population, Need GOOD GPU. between 100_000 - 2_000_000 recommended
        AGENT_SPEED=5,
        TURN_SPEED=1.9,
        SENSOR_ANGLE_DEG=30.0,
        SENSOR_DISTANCE=3,

        # Keep deposit moderate, but rely on blur to inflate "cells"
        DEPOSIT_AMOUNT=0.15,
        AGENT_DEPOSIT_SCALE=1_000_000,  # scales deposit based on total agent count

        USE_RANDOM_SEEDS=True,
        RANDOM_TURN_FACTOR=0.01,

        EVAPORATION_FACTOR=0.92,  # fade slower -> stronger "walls"
        BLUR_RADIUS=1,  # bigger blur => bubble walls
        BLUR_PASSES=1,  # 2 passes each frame

        USE_OBSTACLES=False,
        OBSTACLE_IMAGE="obstacles.png",

        COLOR_MODE="G",  # sum channels => white
        COLOR_MULTIPLIER=60.0,  # fairly high brightness
        BACKGROUND_COLOR=(0.0, 0.0, 0.0, 1.0),
        TARGET_FPS=60,

        SCREENSHOT_KEY=ord('F'),
        SCREENSHOT_FILE="preset1_screenshot.png"
    ),

    #---------------------------------------------------------
    # 4) "Wrinkled Lines" pattern
    #---------------------------------------------------------
    4: dict(
        WINDOW_WIDTH   = 1280,
        WINDOW_HEIGHT  = 720,
        SIM_WIDTH      = 1024,
        SIM_HEIGHT     = 1024,

        MULTI_SPECIES  = False,
        NUM_SPECIES    = 1,

        NUM_AGENTS       = 1_000_000,
        AGENT_SPEED      = 9,
        TURN_SPEED       = 0.15,
        SENSOR_ANGLE_DEG = 20.0,
        SENSOR_DISTANCE  = 6.0,

        DEPOSIT_AMOUNT      = 0.008,
        AGENT_DEPOSIT_SCALE = 1_000_000,

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.03, # more wiggle => wavy lines

        EVAPORATION_FACTOR = 0.97,
        BLUR_RADIUS        = 1,
        BLUR_PASSES        = 1,

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        # We'll do "CUSTOM" for a bluish highlight
        COLOR_MODE       = "G",
        COLOR_MULTIPLIER = 50.0,
        BACKGROUND_COLOR = (0.0, 0.0, 0.0, 1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset4_screenshot.png"
    ),

    #---------------------------------------------------------
    # 5) "Sparse Minimal Lines"
    #   - fewer agents, very low deposit => faint lines
    #---------------------------------------------------------
    5: dict(
        WINDOW_WIDTH   = 1280,
        WINDOW_HEIGHT  = 720,
        SIM_WIDTH      = 1024,
        SIM_HEIGHT     = 1024,

        MULTI_SPECIES  = False,
        NUM_SPECIES    = 1,

        NUM_AGENTS       = 50_000,
        AGENT_SPEED      = 0.3,
        TURN_SPEED       = 0.25,
        SENSOR_ANGLE_DEG = 28.0,
        SENSOR_DISTANCE  = 6.0,

        DEPOSIT_AMOUNT      = 0.02,
        AGENT_DEPOSIT_SCALE = 50_000,

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.02,

        EVAPORATION_FACTOR = 0.94,
        BLUR_RADIUS        = 1,
        BLUR_PASSES        = 1,

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        COLOR_MODE       = "SUM",
        COLOR_MULTIPLIER = 40.0,
        BACKGROUND_COLOR = (0.0, 0.0, 0.0, 1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset5_screenshot.png"
    ),

    #---------------------------------------------------------
    # 6) "Dense Liquid Web"
    #   - higher deposit, faster fade => netlike
    #---------------------------------------------------------
    6: dict(
        WINDOW_WIDTH   = 1280,
        WINDOW_HEIGHT  = 720,
        SIM_WIDTH      = 1024,
        SIM_HEIGHT     = 1024,

        MULTI_SPECIES  = False,
        NUM_SPECIES    = 1,

        NUM_AGENTS       = 350_000,
        AGENT_SPEED      = 0.4,
        TURN_SPEED       = 0.35,
        SENSOR_ANGLE_DEG = 30.0,
        SENSOR_DISTANCE  = 8.0,

        DEPOSIT_AMOUNT      = 0.2,
        AGENT_DEPOSIT_SCALE = 350_000,

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.025,

        EVAPORATION_FACTOR = 0.90,  # faster fade => more dynamic
        BLUR_RADIUS        = 2,
        BLUR_PASSES        = 1,

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        COLOR_MODE       = "SUM",
        COLOR_MULTIPLIER = 70.0,
        BACKGROUND_COLOR = (0.0, 0.0, 0.0, 1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset6_screenshot.png"
    ),

    #---------------------------------------------------------
    # 7) "Two-Species Rainbow" (Multi-Species demonstration)
    #---------------------------------------------------------
    7: dict(
        WINDOW_WIDTH   = 1280,
        WINDOW_HEIGHT  = 720,
        SIM_WIDTH      = 1024,
        SIM_HEIGHT     = 1024,

        MULTI_SPECIES  = True,
        NUM_SPECIES    = 2,

        SPECIES_AGENT_COUNTS = [150_000, 150_000],
        SPECIES_SPEEDS         = [0.3, 0.5],
        SPECIES_TURN_SPEEDS    = [0.3, 0.2],
        SPECIES_SENSOR_ANGLES  = [25.0, 35.0],
        SPECIES_SENSOR_DIST    = [7.0, 10.0],
        SPECIES_DEPOSIT_AMOUNTS= [0.1, 0.1],

        # We'll not even define single-species fields, because multi-species code
        NUM_AGENTS       = 300_000,  # total (some code references this)
        AGENT_SPEED      = 0.0,      # unused for multi
        TURN_SPEED       = 0.0,      # unused
        SENSOR_ANGLE_DEG = 0.0,
        SENSOR_DISTANCE  = 0.0,
        DEPOSIT_AMOUNT   = 0.0,

        AGENT_DEPOSIT_SCALE = 300_000,

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.02,

        EVAPORATION_FACTOR = 0.94,
        BLUR_RADIUS        = 2,
        BLUR_PASSES        = 1,

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        COLOR_MODE       = "RGB",  # so species 0 => R, species 1 => G => might look yellowish
        COLOR_MULTIPLIER = 80.0,
        BACKGROUND_COLOR = (0.0, 0.0, 0.0, 1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset7_screenshot.png"
    ),

    #---------------------------------------------------------
    # 8) "Two-Species Complimentary" (one species = R, the other = B)
    #---------------------------------------------------------
    8: dict(
        WINDOW_WIDTH   = 1280,
        WINDOW_HEIGHT  = 720,
        SIM_WIDTH      = 1024,
        SIM_HEIGHT     = 1024,

        MULTI_SPECIES  = True,
        NUM_SPECIES    = 2,

        SPECIES_AGENT_COUNTS = [200_000, 200_000],
        SPECIES_SPEEDS         = [0.35, 0.35],
        SPECIES_TURN_SPEEDS    = [0.3, 0.3],
        SPECIES_SENSOR_ANGLES  = [30.0, 30.0],
        SPECIES_SENSOR_DIST    = [8.0, 8.0],
        SPECIES_DEPOSIT_AMOUNTS= [0.08, 0.08],

        NUM_AGENTS         = 400_000,
        AGENT_SPEED        = 0.0,  # unused single fields
        TURN_SPEED         = 0.0,
        SENSOR_ANGLE_DEG   = 0.0,
        SENSOR_DISTANCE    = 0.0,
        DEPOSIT_AMOUNT     = 0.0,

        AGENT_DEPOSIT_SCALE= 400_000,

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.02,

        EVAPORATION_FACTOR = 0.96,
        BLUR_RADIUS        = 2,
        BLUR_PASSES        = 2, # slightly bigger blur

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        COLOR_MODE       = "RGB",  # species 0 => R, species 1 => G, ignoring B => might see red + green
                                   # If you want red+blue, either do species 0 => R, species 1 => B => but code
                                   # always uses channel 1 => G. You can adapt or do "CUSTOM" for real red+blue
        COLOR_MULTIPLIER = 70.0,
        BACKGROUND_COLOR = (0.0, 0.0, 0.0, 1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset8_screenshot.png"
    ),

    #---------------------------------------------------------
    # 9) "Obstacle Maze" demonstration
    #   (requires obstacles.png for a shape or labyrinth)
    #---------------------------------------------------------
    9: dict(
        WINDOW_WIDTH   = 1280,
        WINDOW_HEIGHT  = 720,
        SIM_WIDTH      = 1024,
        SIM_HEIGHT     = 1024,

        MULTI_SPECIES  = False,
        NUM_SPECIES    = 1,

        NUM_AGENTS       = 150_000,
        AGENT_SPEED      = 0.4,
        TURN_SPEED       = 0.3,
        SENSOR_ANGLE_DEG = 25.0,
        SENSOR_DISTANCE  = 8.0,

        DEPOSIT_AMOUNT      = 0.1,
        AGENT_DEPOSIT_SCALE = 150_000,

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.02,

        EVAPORATION_FACTOR = 0.95,
        BLUR_RADIUS        = 1,
        BLUR_PASSES        = 1,

        USE_OBSTACLES = True,   # put a labyrinth or shape in obstacles.png
        OBSTACLE_IMAGE= "labyrinth.png",

        COLOR_MODE       = "SUM",
        COLOR_MULTIPLIER = 60.0,
        BACKGROUND_COLOR = (0.0,0.0,0.0,1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset9_screenshot.png"
    ),

    #---------------------------------------------------------
    # 10) "Fast Flicker"
    #   - quick fade, no blur => sharp ephemeral lines
    #---------------------------------------------------------
    10: dict(
        WINDOW_WIDTH  = 1280,
        WINDOW_HEIGHT = 720,
        SIM_WIDTH     = 1024,
        SIM_HEIGHT    = 1024,

        MULTI_SPECIES = False,
        NUM_SPECIES   = 1,

        NUM_AGENTS       = 100_000,
        AGENT_SPEED      = 0.5,
        TURN_SPEED       = 0.4,
        SENSOR_ANGLE_DEG = 25.0,
        SENSOR_DISTANCE  = 6.0,

        DEPOSIT_AMOUNT      = 0.05,
        AGENT_DEPOSIT_SCALE = 100_000,

        USE_RANDOM_SEEDS   = True,
        RANDOM_TURN_FACTOR = 0.02,

        EVAPORATION_FACTOR = 0.85,  # fast fade => ephemeral lines
        BLUR_RADIUS        = 0,     # no blur
        BLUR_PASSES        = 0,

        USE_OBSTACLES = False,
        OBSTACLE_IMAGE= "obstacles.png",

        COLOR_MODE       = "SUM",
        COLOR_MULTIPLIER = 50.0,
        BACKGROUND_COLOR = (0.0,0.0,0.0,1.0),
        TARGET_FPS       = 60,

        SCREENSHOT_KEY  = ord('F'),
        SCREENSHOT_FILE = "preset10_screenshot.png"
    )

}


# Now we'll extract the chosen preset from ALL_PRESETS using CURRENT_PRESET
CHOSEN = ALL_PRESETS.get(CURRENT_PRESET, ALL_PRESETS[1])  # fallback to #1 if invalid

# Then we define all the config variables from that dictionary for easy usage,
# you can also set them to a specific value if needed, but then remove 'CHOSEN'
WINDOW_WIDTH       = 3840
WINDOW_HEIGHT      = 2160
SIM_WIDTH          = 3840
SIM_HEIGHT      = 2160

MULTI_SPECIES      = CHOSEN["MULTI_SPECIES"]
NUM_SPECIES        = CHOSEN["NUM_SPECIES"]

NUM_AGENTS         = CHOSEN["NUM_AGENTS"]
AGENT_SPEED        = CHOSEN["AGENT_SPEED"]
TURN_SPEED         = CHOSEN["TURN_SPEED"]
SENSOR_ANGLE_DEG   = CHOSEN["SENSOR_ANGLE_DEG"]
SENSOR_DISTANCE    = CHOSEN["SENSOR_DISTANCE"]
DEPOSIT_AMOUNT     = CHOSEN["DEPOSIT_AMOUNT"]
AGENT_DEPOSIT_SCALE= CHOSEN["AGENT_DEPOSIT_SCALE"]

USE_RANDOM_SEEDS   = CHOSEN["USE_RANDOM_SEEDS"]
RANDOM_TURN_FACTOR = CHOSEN["RANDOM_TURN_FACTOR"]

EVAPORATION_FACTOR = CHOSEN["EVAPORATION_FACTOR"]
BLUR_RADIUS        = CHOSEN["BLUR_RADIUS"]
BLUR_PASSES        = CHOSEN["BLUR_PASSES"]

USE_OBSTACLES      = CHOSEN["USE_OBSTACLES"]
OBSTACLE_IMAGE     = CHOSEN["OBSTACLE_IMAGE"]

COLOR_MODE         = CHOSEN["COLOR_MODE"]
COLOR_MULTIPLIER   = CHOSEN["COLOR_MULTIPLIER"]
BACKGROUND_COLOR   = CHOSEN["BACKGROUND_COLOR"]
TARGET_FPS         = CHOSEN["TARGET_FPS"]

SCREENSHOT_KEY     = CHOSEN["SCREENSHOT_KEY"]
SCREENSHOT_FILE    = CHOSEN["SCREENSHOT_FILE"]

# For multi-species arrays (only used if MULTI_SPECIES=True)
# We'll define placeholders if the keys exist:
if MULTI_SPECIES:
    SPECIES_AGENT_COUNTS   = CHOSEN["SPECIES_AGENT_COUNTS"]
    SPECIES_SPEEDS         = CHOSEN["SPECIES_SPEEDS"]
    SPECIES_TURN_SPEEDS    = CHOSEN["SPECIES_TURN_SPEEDS"]
    SPECIES_SENSOR_ANGLES  = CHOSEN["SPECIES_SENSOR_ANGLES"]
    SPECIES_SENSOR_DIST    = CHOSEN["SPECIES_SENSOR_DIST"]
    SPECIES_DEPOSIT_AMOUNTS= CHOSEN["SPECIES_DEPOSIT_AMOUNTS"]
