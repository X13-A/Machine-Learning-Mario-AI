# Debug parameters
SHOW_FPS = False
AVERAGE_FPS_CALCULATION_TIME = 20
MAX_FRAMERATE = 60000000
SHOW_MINI_DISPLAY = False
RENDER_MODE = "human" # [human | none]
LOG_HIGHSCORE = True
WIN_SCORE = 2800

# Learning parameters
ENABLE_TRAINING = True
EPSILON_MIN = 0.05
EPSILON_START = 0.05
EPSILON_SCALING = 0.9999
GAMMA = 0.9
ALPHA = 0.1
VISION_RANGE = 6
MAX_STUCK_TIME = 1000
DEATH_PENALTY = -150
STAND_STILL_PENALTY = -2
FRAMES_BEFORE_UPDATE = 60//60
SPEEDRUN_ACTIONS = [3,4]
IDLE_ACTION = 0

# Path parameters
SCORES_STORAGE_PATH = 'score_graph.json'
