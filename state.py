import pygame, math
from maze_generator import *
from collections import OrderedDict
pygame.init()

# Size and Screen Setup
WIDTH, HEIGHT = 800, 450
center_y = HEIGHT // 2
screen = pygame.display.set_mode((WIDTH, HEIGHT), vsync=True)
FPS = 60

# Worldgrid
GRID_WIDTH = 32
GRID_HEIGHT = 32
cur_size = 32
world = wilsons_maze(GRID_HEIGHT, GRID_HEIGHT, 6)

# World Generation - Helper Funcs
def get_empty_cells(world):
    size = len(world)-1
    empty_cells = [(y, x) for y in range(size) for x in range(size) if world[y, x] == 0]
    return empty_cells
def set_spawn_and_end(world):
    height, width = len(world), len(world[0])

    # Sucht Sackgassen am rechten Rand (Prüfung ob nur ein Weg hin Möglich)
    goal_points = [
        (y, width-2) for y in range(height-2)
        if (world[y][width-2] == 0) and
       ( (world[y-1][width-2] == 0 and world[y+1][width-2] != 0 and world[y][width-3] != 0) or
        (world[y+1][width-2] == 0 and world[y-1][width-2] != 0 and world[y][width-3] != 0) or
        (world[y+1][width-2] != 0 and world[y-1][width-2] != 0 and world[y][width-3] == 0))
    ]
    # Notlösung falls keine Sackgassen am Rand
    if not goal_points:
        goal_points = [(y, width-2) for y in range(1, height-2) if world[y][width-2] == 0]

    p1 = random.choice(goal_points)
    world[p1] = 2

    spawn_points = [(y, 1) for y in range(height-1) if world[y][1] == 0]
    p2 = random.choice(spawn_points)

    return p1, p2

# Player state
end_pos, player_spawn = set_spawn_and_end(world)
player_y, player_x = player_spawn
player_energy = 100
player_speed_mult = 1
player_view = None

# Camera
FOV = math.radians(60)
player_angle = math.radians(0)
cam_pitch = 0
walk_cycle = 0
bob_offset_x = bob_offset_y = 0

PLAYING = False
TIMER = 0

# Drawing
SPRITES = []
MAX_DISTANCE = 32
MAX_VIEW_DISTANCE = 8
PROJ_PLANE = (WIDTH / 2) / math.tan(FOV * 0.5)
Z_BUFFER = [0.0] * WIDTH
QUANTIZE_HEIGHT = 4
RAY_STEP = 8
BRIGHTNESS_FALLOFF = 2

def get_cached_column(cache_key, texture, texture_x, target_height):
    col_surf = column_cache.get(cache_key)
    if col_surf is not None:
        column_cache.move_to_end(cache_key)
        return col_surf

    texture_height = texture.get_height()
    tx = max(0, min(texture.get_width() - 1, texture_x))
    tex_col = texture.subsurface((tx, 0, 1, texture_height))
    col_surf = pygame.transform.scale(tex_col, (RAY_STEP, target_height))

    column_cache[cache_key] = col_surf
    if len(column_cache) > CACHE_MAX_SIZE:
        column_cache.popitem(last=False)
    return col_surf
column_cache = OrderedDict()
CACHE_MAX_SIZE = 4096
