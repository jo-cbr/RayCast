import math, pygame

FPS = 60

WIDTH, HEIGHT = 1920, 1080
center_y = HEIGHT // 2
screen = pygame.display.set_mode((WIDTH, HEIGHT), vsync=True)

PROJ_PLANE = (WIDTH / 2) / math.tan(math.radians(60) * 0.5)
QUANTIZE_HEIGHT = 4
RAY_STEP = 8
BRIGHTNESS_FALLOFF = 2
Z_BUFFER = [0.0] * WIDTH
MAX_DISTANCE = 32
MAX_VIEW_DISTANCE = 8

CACHE_MAX_SIZE = 4096