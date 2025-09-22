import pygame, math, random, cProfile
from pygame_button import Button
from maze_generator import *
from collections import OrderedDict

pygame.init()
pygame.mixer.init()

clock = pygame.time.Clock()
FPS = 60

GRID_WIDTH = 32
GRID_HEIGHT = 32
world = wilsons_maze(GRID_HEIGHT, GRID_HEIGHT, 6)
cur_size = 32

MAX_DISTANCE = 32
MAX_VIEW_DISTANCE = 8

WIDTH, HEIGHT = 1920, 1080
screen = pygame.display.set_mode((WIDTH, HEIGHT), vsync=True)
center_y = HEIGHT // 2

FOV = math.radians(60)
player_angle = math.radians(0)

cam_pitch = 0
walk_cycle = 0
bob_offset_x = bob_offset_y = 0

Z_BUFFER = [0.0] * WIDTH
def set_spawn_and_end():

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

end_pos, player_spawn = set_spawn_and_end()
player_y, player_x = player_spawn

player_energy = 100
player_speed_mult = 1
player_view = None
PLAYING = False

TIMER = 0

#region Soundeffects
background_channel = pygame.mixer.Channel(0)

background_sound = pygame.mixer.Sound('assets/background_sound.mp3')
background_sound.set_volume(0.1)

footstep_channel = pygame.mixer.Channel(1)
footstep_channel.set_volume(0.1)

footstep_reg = pygame.mixer.Sound('assets/footsteps_reg.mp3')
footstep_reg.set_volume(0.1)
footstep_sprint = pygame.mixer.Sound('assets/footsteps_sprint.mp3')
footstep_sprint.set_volume(0.2)
exhausted = pygame.mixer.Sound('assets/exhausted.mp3')
exhausted.set_volume(2)

random_sound_channel = pygame.mixer.Channel(2)
random_sound_channel.set_source_location(180, 5)
wind_sound = pygame.mixer.Sound('assets/wind_sound.mp3')
wind_sound.set_volume(1.1)
intense_sound = pygame.mixer.Sound('assets/intense_suspense.mp3')
intense_sound.set_volume(0.2)
footsteps_behind = pygame.mixer.Sound('assets/footsteps_behind.mp3')
humming = pygame.mixer.Sound('assets/humming.mp3')
ghost_sound = pygame.mixer.Sound('assets/ghost_sound.mp3')
branch_cracking = pygame.mixer.Sound('assets/cracking_sound.mp3')
branch_cracking.set_volume(0.8)
death_sound = pygame.mixer.Sound('assets/death_beep.mp3')
death_sound.set_volume(0.7)

heartbeat_channel = pygame.mixer.Channel(3)
heartbeat_slow = pygame.mixer.Sound('assets/heartbeat_slow.mp3')
heartbeat_medium = pygame.mixer.Sound('assets/heartbeat_medium.mp3')
heartbeat_fast = pygame.mixer.Sound('assets/heartbeat_fast.mp3')

def handle_random_sounds():
    global random_sound_channel
    rare_sounds = [wind_sound, footsteps_behind, intense_sound, branch_cracking, humming, ghost_sound]
    if random.random() > 0.9999 and not random_sound_channel.get_busy():
        random_sound_channel.play(random.choice(rare_sounds))

#endregion
PROJ_PLANE = (WIDTH / 2) / math.tan(FOV * 0.5)

#region Textures
BG_IMAGE = pygame.image.load('assets/main_background.png').convert()

WALL_TEXTURE = pygame.image.load('assets/bushwall.png').convert()
CHECKPOINT_WALL_TEXTURE = pygame.image.load('assets/checkpoint_wall.png').convert()
SAVED_CHECKPOINT_WALL_TEXTURE = pygame.image.load('assets/saved_checkpoint_wall.png').convert()
GOAL_WALL_TEXTURE = pygame.image.load('assets/goal_wall.png').convert()

WALL_TEXTURE_WIDTH, WALL_TEXTURE_HEIGHT = WALL_TEXTURE.get_size()

VIGNETTE_SURF = pygame.image.load('assets/vignette.png').convert_alpha()
VIGNETTE_SURF = pygame.transform.scale(VIGNETTE_SURF, screen.get_size()).convert_alpha()

GLOWSTICK_TEXTURE = pygame.transform.scale_by(pygame.image.load('assets/glowstick.png').convert_alpha(), 16)
glowstick_colors = [
    (255, 0, 0), (0, 255, 0),
    (0, 0, 255), (255, 255, 0),
    (0, 255, 255), (255, 0, 255), 
    (255, 200, 0), (128, 0, 255)
]

TORCH_TEXTURE = pygame.image.load('assets/items/torch.png').convert_alpha()
CRYSTAL_BALL_TEXTURE = pygame.image.load('assets/items/crystal_ball.png').convert_alpha()
CROSS_TEXTURE = pygame.image.load('assets/items/jesus_cross.png').convert_alpha()
SPEED_BOOST_TEXTURE = pygame.image.load('assets/items/sprint_boost.png').convert_alpha()

#endregion
column_cache = OrderedDict()
CACHE_MAX_SIZE = 4096
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


QUANTIZE_HEIGHT = 4

RAY_STEP = 8

BRIGHTNESS_FALLOFF = 2
#region Draw Funcs
def draw_scene():
    screen.fill((0, 0, 0))
    ray_data = cast_rays()
    draw_ray_data(ray_data)
    draw_sprites(SPRITES)
    draw_energy()
    draw_timer()
    screen.blit(VIGNETTE_SURF, (0, 0))

def draw_energy():
    c = int(255*(player_energy/100))
    color = (255, c, c)
    energy_rect = pygame.Rect(int(WIDTH*0.02), int(HEIGHT*0.02), int(WIDTH*0.2*(player_energy/100)), int(HEIGHT*0.03))
    bg_rect = pygame.Rect(int(WIDTH*0.02), int(HEIGHT*0.02), int(WIDTH*0.2), int(HEIGHT*0.03))
    pygame.draw.rect(screen, (92, 92, 92), bg_rect)
    pygame.draw.rect(screen, color, energy_rect)

def draw_timer():
    minutes = TIMER//60
    seconds = TIMER%60
    text = f'{int(minutes):02}:{round(seconds):02}'
    timer_font = pygame.font.SysFont('Garamond', 32, False)
    timer_rec = timer_font.render(text, True, (128,128,128))
    pos = (WIDTH//2-timer_rec.get_width()//2, HEIGHT - 1.2*timer_rec.get_height())
    screen.blit(timer_rec, pos)

def draw_ray_data(ray_data):
    textures = {
        1: WALL_TEXTURE,
        2: GOAL_WALL_TEXTURE,
        #3: MARKED_WALL_TEXTURE,
        4: CHECKPOINT_WALL_TEXTURE,
        5: SAVED_CHECKPOINT_WALL_TEXTURE,
    }
    ray_blits = []

    for ray in ray_data:
        wall_height, screen_x, distance, side, grid_value, text_x, wall_pos = ray
        texture = textures[grid_value]
        result = draw_ray(int(wall_height), screen_x, distance, side, grid_value, text_x, texture)
        if result:
            ray_blits.append(result)

    if ray_blits:
        screen.blits(ray_blits)

def draw_ray(wall_height, screen_x, distance, side, grid_value, texture_x, texture):
    final_x = screen_x + bob_offset_x
    if not 0 <= final_x < WIDTH:
        return

    if wall_height <= 0:
        return

    if distance >= MAX_DISTANCE:
        return


    target_height = min(max(1, wall_height), HEIGHT*5)
    target_height = (target_height // QUANTIZE_HEIGHT) * QUANTIZE_HEIGHT
    
    half_h = target_height // 2

    top_y = int(center_y - half_h + bob_offset_y + cam_pitch)


    cache_key = (texture_x, target_height, grid_value)
    col_surf = get_cached_column(cache_key, texture, texture_x, target_height)


    # Helligkeit managen
    norm_distance = distance / MAX_VIEW_DISTANCE
    brightness = BRIGHTNESS_FALLOFF * (norm_distance ** 2)
    brightness = min(max(brightness, 0), 1)

    col_surf_final = col_surf.copy()

    sc = 128 * brightness + (10 if side else 0)
    shadow_color = (sc, sc, sc)

    # Legt finales "Schatten Layer" über Surface
    col_surf_final.fill(shadow_color, special_flags=pygame.BLEND_SUB)

    col_blit = (col_surf_final, (final_x, top_y))
    return col_blit

SPRITES = []

def draw_sprites(sprites):
    if len(sprites) == 0:
        return
    
    half_fov = FOV*0.5

    dir_x = math.cos(player_angle)
    dir_y = math.sin(player_angle)
    plane_x = -dir_y * math.tan(half_fov)
    plane_y = dir_x * math.tan(half_fov)

    det = plane_x * dir_y - dir_x * plane_y
    inv_det = 1 / det

    blits = []

    # Sprites nach Distanz sortieren
    sprites.sort(key = lambda s: (s['x']-player_x)**2 + (s['y']-player_y)**2, reverse=True)
    for sprite in sprites:
        sprite_x = sprite['x'] - player_x
        sprite_y = sprite['y'] - player_y

        texture = sprite['texture']
        texture_width = texture.get_width()
        texture_height = texture.get_height()
        
        transform_x = inv_det * (dir_y * sprite_x - dir_x * sprite_y)
        transform_y = inv_det * (-plane_y * sprite_x + plane_x * sprite_y)
        if transform_y < 0.1:
            continue
        sprite_screen_x = int((WIDTH/2) * (1 + transform_x / transform_y))
        if not (-texture_width <= sprite_screen_x < WIDTH):
            continue

        proj_wall_h = int((1.0 / transform_y) * PROJ_PLANE)
        if proj_wall_h > HEIGHT*5:
            continue

        sprite_height = abs(int(texture_height / transform_y))
        sprite_width = abs(int(texture_width / transform_y))
        
        wall_bottom_y = int(center_y + proj_wall_h//2 + cam_pitch + bob_offset_y)
        if wall_bottom_y - sprite_height > HEIGHT:
            continue
        elif wall_bottom_y + sprite_height < 0:
            continue

        draw_start_y = wall_bottom_y - sprite_height
        
        draw_start_x = -sprite_width // 2 + sprite_screen_x
        if draw_start_x < -sprite_width: draw_start_x = 0
        draw_end_x = sprite_width // 2 + sprite_screen_x
        if draw_end_x >= WIDTH: draw_end_x = WIDTH - 1

        scaled_texture = pygame.transform.scale(texture, (sprite_width, sprite_height))
        for stripe in range(draw_start_x, draw_end_x):
            if stripe < 0 or stripe > WIDTH: continue
            if transform_y < Z_BUFFER[stripe]:
                tex_x = min(int((stripe - draw_start_x) * scaled_texture.get_width() / sprite_width), scaled_texture.get_width()-10)
                column = scaled_texture.subsurface((tex_x, 0, 8, sprite_height))

                blits.append((column, (stripe, draw_start_y)))

    if len(blits) > 0:
        screen.blits(blits)

#endregion

#region Ray Cast Funcs
def cast_rays():
    ray_data = []
    half_fov = FOV * 0.5
    map_x = int(player_x)
    map_y = int(player_y)

    cos_vals = []
    sin_vals = []
    cos_corrections = []

    for idx, i in enumerate(range(0, WIDTH, RAY_STEP)):
        ray_angle = player_angle - half_fov + (i/WIDTH) * FOV
        cos_vals.append(math.cos(player_angle - FOV*0.5 + (i/WIDTH) * FOV))
        sin_vals.append(math.sin(player_angle - FOV*0.5 + (i/WIDTH) * FOV))
        cos_corrections.append(math.cos(ray_angle - player_angle))

    for idx, i in enumerate(range(0, WIDTH, RAY_STEP)):
        dir_x = cos_vals[idx]
        dir_y = sin_vals[idx]
        cos_correction = cos_corrections[idx]
        data = cast_single_ray(i, map_x, map_y, dir_x, dir_y, cos_correction)
        ray_data.append(data)
    return ray_data

def cast_single_ray(i, map_x, map_y, dir_x, dir_y, cos_correction):
    global Z_BUFFER
    # Strecke pro Spalte
    delta_distance_x = abs(1 / dir_x) if dir_x != 0 else 1e30
    delta_distance_y = abs(1 / dir_y) if dir_y != 0 else 1e30

    side = 0

    # Entfernung zur nähsten Spalte
    if dir_x < 0: # nächster schnittpunkt liegt rechts
        side_dist_x = (player_x - map_x) * delta_distance_x
        step_x = -1
    else: # links
        side_dist_x = (map_x + 1 - player_x) * delta_distance_x
        step_x = 1
    if dir_y < 0:
        step_y = -1
        side_dist_y = (player_y - map_y) * delta_distance_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - player_y) * delta_distance_y

    hit = False
    grid_value = 1
    raw_dist = 0
    
    while not hit:
        if side_dist_x < side_dist_y:
            side_dist_x += delta_distance_x
            map_x += step_x
            side = 0
            raw_dist = side_dist_x - delta_distance_x
        elif side_dist_y < side_dist_x:
            side_dist_y += delta_distance_y
            map_y += step_y
            side = 1
            raw_dist = side_dist_y - delta_distance_y
        else: # Wenn Ecke
            side_dist_x += delta_distance_x
            map_x += step_x
            side_dist_y += delta_distance_y
            map_y += step_y
            side = 0
            raw_dist = (side_dist_x - delta_distance_x + side_dist_y - delta_distance_y) / 2


        if map_x < 0 or map_y < 0 or map_x >= GRID_WIDTH or map_y >= GRID_WIDTH:
            raw_dist = min(raw_dist, MAX_DISTANCE)
            break

        grid_value = world[map_y, map_x]
        if 0 <= map_x < GRID_WIDTH and 0 <= map_y < GRID_HEIGHT:
            if grid_value != 0:
                hit = True
        else:
            # außerhalb: clamp
            raw_dist = min(raw_dist, MAX_DISTANCE)
            hit = True

    perp_distance = max(raw_dist * cos_correction, 0.01)
    if side == 0:
        wall_coord = player_y + raw_dist * dir_y
    else:
        wall_coord = player_x + raw_dist * dir_x

    wall_coord -= math.floor(wall_coord)

    text_x = int(wall_coord*(WALL_TEXTURE_WIDTH-1))
    text_x = max(0, min(WALL_TEXTURE_WIDTH - 1, text_x))

    # Flippen je nach Seite
    if not side and dir_x > 0:
        text_x = (WALL_TEXTURE_WIDTH - text_x - 1)
    elif side and dir_y < 0:
        text_x = (WALL_TEXTURE_WIDTH - text_x - 1)

    wall_pos = (map_y, map_x)
    wall_height = int((1.0 / perp_distance) * PROJ_PLANE)
    Z_BUFFER[i] = raw_dist

    return wall_height, i, perp_distance, side, grid_value, text_x, wall_pos
#endregion

#region Player Controller Funcs
exhausted_played = False
ENERGY_FACTOR = 1
def player_controller(delta_time):
    # Alle globalen vars die gebraucht werden
    global player_x, player_y, player_angle, player_spawn, \
            cam_pitch, center_y, FOV, player_energy, PLAYING, \
            walk_cycle, bob_offset_y, bob_offset_x, \
            exhausted_played, player_speed_mult

    next_x, next_y = player_x, player_y
    move_speed = 1
    strafe_speed = 0.75
    rot_speed = 45
    energy_loss_factor = 12 * ENERGY_FACTOR
    energy_gain_factor = 5

    moving = False

    base_fov = math.radians(60)
    min_fov = base_fov*0.95 # Beim Sprint base_fov -> min_fov
    dyn_fov_mult = 0.5 # Glättet verlauf der FOV

    view_bob_frequency = 7 # streckt die Sinuswelle
    view_bob_amplitude = 0.1 # in px

    forward = 0
    strafe = 0

    if pygame.event.get_grab():
        mouse_x, mouse_y = pygame.mouse.get_rel()
        if mouse_x != 0:
            norm_mouse_x = mouse_x/WIDTH
            player_angle += norm_mouse_x * rot_speed * delta_time
        if mouse_y != 0:
            cam_pitch -= mouse_y * rot_speed * delta_time
            cam_pitch = min(max(cam_pitch, -HEIGHT), HEIGHT)

        if pygame.mouse.get_just_released()[0]:
            dir_x = math.cos(player_angle)
            dir_y = math.sin(player_angle)
            result = cast_single_ray(int(WIDTH*0.5), FOV*0.5,int(player_x), int(player_y), dir_x, dir_y)
            if result[4] == 2 and result[2] <= 1.5:
                PLAYING = False
                menu()
            if result[4] == 4 and result[2] <= 1.5:
                world[result[6]] = 5
                player_spawn = int(player_x) + 0.5, int(player_y) + 0.5

    if forward < 1.5 and player_energy < 100:
        player_energy += energy_gain_factor * delta_time
        player_energy = min(player_energy, 100)
        
    if player_energy > 25:
        exhausted_played = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        if keys[pygame.K_LSHIFT]:
            forward = 0.75
        elif keys[pygame.K_LCTRL] and not exhausted_played:
            if player_energy > 0:
                forward = 2
                player_energy -= energy_loss_factor * delta_time
                if player_energy <= 0:
                    player_energy = 0
                    random_sound_channel.play(exhausted)
                    exhausted_played = True
            if FOV > min_fov:
                FOV -= (FOV - min_fov) * dyn_fov_mult * delta_time
        else:
            if FOV < base_fov:
                FOV += (base_fov - FOV) * dyn_fov_mult * delta_time
            forward = 1

    if keys[pygame.K_s]:
        forward = -0.5
    if keys[pygame.K_a]:
        strafe = -1
    if keys[pygame.K_d]:
        strafe = 1

    next_x += math.cos(player_angle) * move_speed * forward * delta_time * player_speed_mult
    next_y += math.sin(player_angle) * move_speed * forward * delta_time * player_speed_mult
    next_x += -math.sin(player_angle) * strafe_speed * strafe * delta_time * player_speed_mult
    next_y += math.cos(player_angle) * strafe_speed * strafe * delta_time * player_speed_mult

    # Potentielle Distanz berechnen. Wird verworfen falls is_empty() auf False läuft
    distance = (next_x - player_x)**2 + (next_y - player_y)**2

    if next_x != player_x:
        if check_distance_to_wall(next_x, player_y):
            if is_empty(next_x, player_y):
                player_x = next_x
                moving = True
    if next_y != player_y:
        if check_distance_to_wall(player_x, next_y):
            if is_empty(player_x, next_y):
                player_y = next_y
                moving = True

    if distance > 0 and moving:
        walk_cycle += distance
        walk_cycle %= math.pi*2
    else:
        walk_cycle -= 0.25
        walk_cycle = max(walk_cycle, 0)


    bob_offset_x = math.cos(walk_cycle * 0.5 * view_bob_frequency) * view_bob_amplitude * forward
    bob_offset_y = view_bob_frequency * math.sin(walk_cycle * view_bob_frequency) * view_bob_amplitude * forward

    if moving and not footstep_channel.get_busy():
        q = footstep_channel.get_queue()
        if forward == 1.5:
            if q != footstep_sprint:
                footstep_channel.stop()
            footstep_channel.play(footstep_sprint)
        elif forward >= 1:
            if q != footstep_reg:
                footstep_channel.stop()
            footstep_channel.play(footstep_reg)
    elif not moving and footstep_channel.get_busy():
        footstep_channel.fadeout(50)
        footstep_channel.stop()

def check_distance_to_wall(px, py, margin = 0.15):
    gx, gy = int(px), int(py)
    if not (0 <= gy < len(world) and 0 <= gx < len(world[0])):
        return False
    if world[gy, gx] != 0:
        return False

    dx = px - gx
    dy = py - gy

    # orthogonal
    neighbors = [
        (gx - 1, gy, dx),      # links
        (gx + 1, gy, 1 - dx),  # rechts
        (gx, gy - 1, dy),      # oben
        (gx, gy + 1, 1 - dy),  # unten
    ]
    for nx, ny, dist_frac in neighbors:
        if 0 <= ny < len(world) and 0 <= nx < len(world[0]):
            if world[ny][nx] != 0 and dist_frac < margin:
                return False
            
    
    # diagonal
    diagonals = [
        (gx - 1, gy - 1, max(dx, dy)),          # oben links
        (gx + 1, gy - 1, max(1 - dx, dy)),      # oben rechts
        (gx - 1, gy + 1, max(dx, 1 - dy)),      # unten links
        (gx + 1, gy + 1, max(1 - dx, 1 - dy)),  # unten rechts
    ]
    for nx, ny, dist_frac in diagonals:
        if 0 <= ny < len(world) and 0 <= nx < len(world[0]):
            if world[ny][nx] != 0 and dist_frac < margin:
                return False

    return True

def is_empty(x, y):
    grid_x = int(x)
    grid_y = int(y)
    if 0 <= grid_y < len(world) and 0 <= grid_x < len(world[0]):
        return world[grid_y][grid_x] == 0
    return False
#endregion

#region Patrolling Enemy
class Patroller:
    def __init__(self):
        self.y, self.x = self.get_start_pos()
        self.dx, self.dy = 0,0
        self.mode = 'Patrolling'
        self.speed = 0.75

        self.current_path = []
        self.cur_dir = 'North'
        self.directions = ['North', 'West', 'South', 'East']

        self.player_seen_pos = None
        self.distance_to_player = MAX_DISTANCE

        self.view_distance = 6
        self.view_angle = math.pi/4

        self.front = pygame.transform.scale_by(pygame.image.load('assets/eyeball.png').convert_alpha(), 20)
        self.right = pygame.transform.scale_by(pygame.image.load('assets/eyeball_side.png').convert_alpha(), 20)
        self.left = pygame.transform.flip(pygame.transform.scale_by(pygame.image.load('assets/eyeball_side.png').convert_alpha(), 20), True, False)
        self.back = pygame.transform.scale_by(pygame.image.load('assets/eyeball_back.png').convert_alpha(), 20)
        self.inactive = pygame.transform.scale_by(pygame.image.load('assets/eyeball_inactive.png').convert_alpha(), 20)
        
        self.active = True        

    def get_start_pos(self) -> tuple[int, int]:
        height = width = len(world)-1
        spawns = []
        for y in range(height-1):
            if world[y][width-2] == 0:
                spawns.append((y, width-2))

        spawn = random.choice(spawns)
        return spawn[0]+0.5, spawn[1]+0.5

    def get_direction_vector(self, direction):
        if direction == 'North': return (1, 0)
        if direction == 'South': return (-1, 0)
        if direction == 'East': return (0, 1)
        if direction == 'West': return (0, -1)
        else: return (0,0)

    def get_target_pos(self):
        idx = self.directions.index(self.cur_dir)
        left_dir = self.directions[(idx + 1) % 4]
        dy, dx = self.get_direction_vector(left_dir)
        ty, tx = int(self.y) + dy, int(self.x) + dx

        if world[ty, tx] == 0:
            return [(ty, tx)]
        
        dy, dx = self.get_direction_vector(self.cur_dir)
        ty, tx = int(self.y) + dy, int(self.x) + dx
        if world[ty, tx] == 0:
            return [(ty, tx)]
        
        right_dir = self.directions[(idx + 3) % 4]
        dy, dx = self.get_direction_vector(right_dir)
        ty, tx = int(self.y) + dy, int(self.x) + dx
        if world[ty, tx] == 0:
            return [(ty, tx)]
        
        back_dir = self.directions[(idx + 2) % 4]
        dy, dx = self.get_direction_vector(back_dir)
        ty, tx = int(self.y) + dy, int(self.x) + dx
        if world[ty, tx] == 0:
            return [(ty, tx)]

    def has_line_of_sight(self, x0, y0, x1, y1, grid):
        # Bresenham Line of Sight Check, ähnlich wie durch grid wandern in raycast
        x0, y0 = int(x0), int(y0)
        x1, y1 = int(x1), int(y1)

        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            if grid[y0][x0] != 0:
                return False
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
        return True

    def can_see_player(self):
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        if dist > self.view_distance:
            return False

        dir_map = {'North': (1,0), 'South': (-1,0), 'East': (0,1), 'West': (0,-1)}
        dir_vector = dir_map[self.cur_dir]

        angle = math.acos((dx*dir_vector[1] + dy*dir_vector[0]) / (dist+1e-6))
        if angle > self.view_angle:
            return False

        if not self.has_line_of_sight(self.x, self.y, player_x, player_y, world):
            return False

    def move_and_collide(self, deltatime):
        step_x = self.dx * self.speed * deltatime * (1.5 if self.mode == 'Chasing' else 1)
        step_y = self.dy * self.speed * deltatime * (1.5 if self.mode == 'Chasing' else 1)

        new_x = self.x + step_x
        new_y = self.y + step_y
        radius = 0.05

        cells_x = [
            (int(self.y - radius), int(new_x - radius)),
            (int(self.y - radius), int(new_x + radius)),
            (int(self.y + radius), int(new_x - radius)),
            (int(self.y + radius), int(new_x + radius)),
        ]
        if all(0 <= cy < len(world) and 0 <= cx < len(world[0]) and world[cy][cx] == 0 for cy, cx in cells_x):
            self.x = new_x
        else:
            step_x = 0

        cells_y = [
            (int(new_y - radius), int(self.x - radius)),
            (int(new_y - radius), int(self.x + radius)),
            (int(new_y + radius), int(self.x - radius)),
            (int(new_y + radius), int(self.x + radius)),
        ]
        if all(len(world) > cy >= 0 == world[cy][cx] and 0 <= cx < len(world[0]) for cy, cx in cells_y):
            self.y = new_y
        else:
            step_y = 0

        move_len = math.sqrt(step_x ** 2 + step_y ** 2)
        if move_len > 1e-6:
            self.dx = step_x / move_len
            self.dy = step_y / move_len
        else:
            self.dx, self.dy = 0, 0

    def heartbeat_sound(self, distance_to_player, chasing=False):
        if 5 < distance_to_player < 7.5:
            sound = heartbeat_slow
        elif distance_to_player <= 5 and not chasing:
            sound = heartbeat_medium
        elif chasing:
            sound = heartbeat_fast
        else:
            sound = None

        if sound is not None:
            if heartbeat_channel.get_sound() != sound:
                heartbeat_channel.fadeout(25)
            if not heartbeat_channel.get_busy():
                heartbeat_channel.play(sound)
            

    def update(self, deltatime):
        global player_x, player_y
        if not self.active:
            return
        self.distance_to_player = math.sqrt((player_x-self.x) ** 2 + (player_y-self.y) ** 2)
        if self.distance_to_player < 8:
            path_to_player = a_star(world, (int(self.y), int(self.x)), (int(player_y), int(player_x)))
        else:
            path_to_player = []
        close_to_player = False

        # Kill Player
        if self.distance_to_player < 0.3:
            random_sound_channel.play(death_sound)
            heartbeat_channel.fadeout(50)
            self.y, self.x = self.get_start_pos()
            player_y, player_x = player_spawn

        # Fallback
        if path_to_player is None:
            return
        
        if self.mode == 'Patrolling':
            if not self.current_path:
                self.current_path = self.get_target_pos()
            if self.distance_to_player < 8:
                # Spieler kann gehört werden wenn zu nah, len statt distance sodass es nicht durch wände geht
                if self.can_see_player() or 0 < (len(path_to_player) < 5 and footstep_channel.get_busy()):
                    self.mode = 'Chasing'
                    self.player_seen_pos = (int(player_y), int(player_x))
                    self.current_path = a_star(world, (int(self.y), int(self.x)), self.player_seen_pos)
                    self.view_angle = math.pi/3

        if self.mode == 'Chasing':
            self.player_seen_pos = (int(player_y), int(player_x))
            if len(path_to_player) > 1:
                path_to_player.pop(0)

            # Logik für verschiedene Szenarien
            if self.distance_to_player > self.view_distance or (self.distance_to_player > self.view_distance/2 and not self.can_see_player()):
                self.mode = 'Patrolling'
                self.view_angle = math.pi/4
            if self.can_see_player():
                if self.distance_to_player < 2:
                    close_to_player = True
                    self.current_path = [(player_y, player_x)]
                else:
                    self.current_path = path_to_player
            elif self.distance_to_player < 2:
                self.current_path = path_to_player
            elif 2 <= self.distance_to_player < 4:
                self.current_path = path_to_player[0:-1]
            else:
                self.current_path = self.get_target_pos()

        if self.current_path is None or len(self.current_path) == 0:
            return

        ty, tx = self.current_path[0]
        if close_to_player:
            vec_x, vec_y = tx - self.x, ty - self.y
        else:
            vec_x, vec_y = tx + 0.5 - self.x, ty + 0.5 - self.y

        dist = math.sqrt(vec_x ** 2 + vec_y ** 2)

        if dist < 0.05:
            self.x, self.y = tx+0.5, ty+0.5
            self.current_path.pop(0)

        if dist > 1e-6:
            self.dx = vec_x / dist
            self.dy = vec_y / dist
        else:
            self.dx, self.dy = 0, 0

        # Blickrichtung anpassen
        if abs(vec_x) > abs(vec_y):
            self.cur_dir = 'East' if vec_x > 0 else 'West'
        else:
            self.cur_dir = 'North' if vec_y > 0 else 'South'

        self.move_and_collide(deltatime)
        if self.distance_to_player <= 8:
            self.heartbeat_sound(self.distance_to_player, self.mode=='Chasing')

    def get_rotation_to_player(self):
        dx_to_player = player_x - self.x
        dy_to_player = player_y - self.y

        vector_to_player = (dx_to_player, dy_to_player)
        direction_vector = (self.dx, self.dy)

        dot = direction_vector[0]*vector_to_player[0] + direction_vector[1]*vector_to_player[1]
        cross = direction_vector[0]*vector_to_player[1] - direction_vector[1]*vector_to_player[0]

        angle = math.atan2(cross, dot)
        return angle

    def as_sprite(self):
        if self.distance_to_player > MAX_VIEW_DISTANCE:
            return {'x': self.x, 'y': self.y, 'texture': pygame.Surface((1, 1))}
        angle = self.get_rotation_to_player()
        
        if not self.active:
            return {'x': self.x, 'y': self.y, 'texture': self.inactive}
        #front
        elif -math.pi/4 <= angle <= math.pi/4:
            self.texture = self.front
        #left
        elif math.pi/4 < angle < 3*math.pi/4:
            self.texture = self.left
        # right
        elif -3*math.pi/4 < angle < -math.pi/4:
            self.texture = self.right
        # back
        else:
            self.texture = self.back
        
        norm_distance = self.distance_to_player / MAX_VIEW_DISTANCE
        norm_distance = min(max(norm_distance, 0), 1)

        brightness = BRIGHTNESS_FALLOFF * (norm_distance ** 2)
        c = int(abs(127 * (1 - brightness)))

        final_text = self.texture.copy()
        final_text.fill((c,c,c), special_flags=pygame.BLEND_MULT)

        return {'x': self.x, 'y': self.y, 'texture': final_text}
#endregion

#region Items
ITEMS = []
class Item:
    def __init__(self, pos):
        global SPRITES
        self.y, self.x = pos
        self.duration = 0
        self.time_passed = 0
        self.ability_used = False
        self.get_random_type()
        self.sprite_dict = {'x': self.x, 'y': self.y, 'texture': self.texture}
        SPRITES.append(self.sprite_dict)

    def get_random_type(self):
        # type = [duration, ability_func, revert_ability_func]
        types = [
            ['torch', 15, self.increase_max_view_dist, self.decrease_max_view_dist, TORCH_TEXTURE],
            ['cross', 30, self.set_patroller_inactive, self.set_patroller_active, CROSS_TEXTURE],
            ['speed_boost', 10, self.speed_up_player, self.slow_down_player, SPEED_BOOST_TEXTURE],
            ['crystal_ball', None, self.show_path, None, CRYSTAL_BALL_TEXTURE]
        ]

        random_type = random.choice(types)

        self.name = random_type[0]
        self.duration = random_type[1]
        self.ability_func = random_type[2]
        self.revert_ability_func = random_type[3]
        self.texture = pygame.transform.scale_by(random_type[4], 20)

    def increase_max_view_dist(self):
        global MAX_VIEW_DISTANCE
        MAX_VIEW_DISTANCE = 16
    def decrease_max_view_dist(self):
        global MAX_VIEW_DISTANCE
        MAX_VIEW_DISTANCE = 8

    def set_patroller_inactive(self):
        global patroller
        patroller.active = False
    def set_patroller_active(self):
        global patroller
        patroller.active = True

    def speed_up_player(self):
        global player_speed_mult
        player_speed_mult = 2
    def slow_down_player(self):
        global player_speed_mult
        player_speed_mult = 1

    def show_path(self):
        path = a_star(world, (int(player_y), int(player_x)), end_pos)
        shown_path = path[1:6]
        for pos in shown_path:
            glowstick_tex = GLOWSTICK_TEXTURE.copy()
            color = random.choice(glowstick_colors)
            glowstick_tex.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
            SPRITES.append({'x': pos[1]+0.5, 'y': pos[0]+0.5, 'texture': glowstick_tex})

    def update(self, deltatime):
        if self.ability_used:
            self.time_passed += deltatime
            if self.time_passed >= self.duration:
                if self.revert_ability_func is not None:
                    self.revert_ability_func()
                self.time_passed = 0
                self.ability_used = False
                ITEMS.remove(self)
            return
        else:
            distance_to_player = (player_x-self.x) ** 2 + (player_y-self.y) ** 2
            if distance_to_player > 1:
                return
            
            if distance_to_player < 0.04:
                if self.ability_func is not None:
                    self.ability_func()
                    self.ability_used = True
                    SPRITES.remove(self.sprite_dict)

def spawn_items():
    empty_cells = [(y, x) for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH) if world[y, x] == 0]
    dead_ends = []
    for pos in empty_cells:
        r, c = pos
        # Prüfen ob Sackgasse
        if ((world[r-1, c] == 0 and world[r+1, c] == 1 and world[r, c-1] == 1 and world[r, c+1] == 1) or
            (world[r-1, c] == 1 and world[r+1, c] == 0 and world[r, c-1] == 1 and world[r, c+1] == 1) or
            (world[r-1, c] == 1 and world[r+1, c] == 1 and world[r, c-1] == 0 and world[r, c+1] == 1) or
            (world[r-1, c] == 1 and world[r+1, c] == 1 and world[r, c-1] == 1 and world[r, c+1] == 0)):
            dead_ends.append((r, c))
    
    random.shuffle(dead_ends)
    for pos in dead_ends:
        if random.randint(1, 10) == 10:
            item_pos = pos[0]+0.5, pos[1]+0.5
            item = Item(item_pos)
            ITEMS.append(item)
#endregion

#region Worldgeneration
def place_checkpoints(start, end):
    empty_cells = [(y, x) for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH) if world[y, x] == 0]
    candidates = []
    for pos in empty_cells:
        r, c = pos
        # Prüfen ob Sackgasse
        if ((world[r-1, c] == 0 and world[r+1, c] == 1 and world[r, c-1] == 1 and world[r, c+1] == 1) or
            (world[r-1, c] == 1 and world[r+1, c] == 0 and world[r, c-1] == 1 and world[r, c+1] == 1) or
            (world[r-1, c] == 1 and world[r+1, c] == 1 and world[r, c-1] == 0 and world[r, c+1] == 1) or
            (world[r-1, c] == 1 and world[r+1, c] == 1 and world[r, c-1] == 1 and world[r, c+1] == 0)):
            candidates.append((r, c))

    steps = math.floor(4 * cur_size/128)
    if steps == 0:
        return
    step_size = cur_size/steps
    for s in range(1, steps):
        start_y = start[0]
        start_x = round(step_size*s)
        end_y = end[0]
        end_x = end[1]

        mid_y = (start_y + end_y) / 2
        mid_x = (start_x + end_x) / 2
        cur_best = min(candidates, key=lambda p: abs(p[0]-mid_y) + abs(p[1]-mid_x))

        world[cur_best] = 4

def create_world():
    global world, player_y, player_x, GRID_HEIGHT, GRID_WIDTH, cur_size
    cur_size += 16
    cur_size %= 144
    cur_size = max(cur_size, 16)

    return cur_size

def loading_screen(text):
    screen.fill((0, 0, 0))
    loading_font = pygame.font.SysFont('Garamond', 32)
    loading_title = text
    loading_text = loading_font.render(loading_title, True, (255, 255, 255))
    text_rect = loading_text.get_rect()
    text_rect.center = (WIDTH//2, HEIGHT//2)
    screen.blit(loading_text, text_rect.topleft)
    pygame.display.update()
#endregion
# Main Loop
patroller = None
def main():
    global cam_pitch, player_view, PLAYING, GRID_HEIGHT, GRID_WIDTH, \
        player_x, player_y, player_spawn, world, TIMER, SPRITES, ENERGY_FACTOR,\
        patroller, end_pos
    mouse_visible = False
    mouse_grab = True
    pygame.mouse.set_visible(mouse_visible)
    pygame.event.set_grab(mouse_grab)

    spray_cooldown = 1.0
    last_sprayed = 1.0
    
    # World Creation and Setup
    if not PLAYING:
        TIMER = 0
        while True:
            loading_screen('Generating Maze...')
            world = wilsons_maze(cur_size, cur_size, 5)
            GRID_HEIGHT, GRID_WIDTH = len(world), len(world[0])
            # Pathfind weg erstellen
            end_pos, start_pos = set_spawn_and_end()
            maze_path = a_star(world, start_pos, end_pos)
            if maze_path is None:
                continue
            if len(maze_path) > cur_size:
                break

        if GRID_HEIGHT > 16:
            loading_screen('Placing Checkpoints...')
            place_checkpoints(start_pos, end_pos)

        SPRITES=[]
        loading_screen('Spawning Enemies...')
        patroller = Patroller()

        loading_screen('Placing Items...')
        spawn_items()

        player_spawn = player_y, player_x = start_pos[0] + 0.5, start_pos[1] + 0.5
        SPRITES.append({'x': patroller.x, 'y': patroller.y, 'texture': patroller.front})

        ENERGY_FACTOR = 128/cur_size
        PLAYING = True

    # Fallback
    if patroller is None:
        patroller = Patroller()

    clock.tick(FPS)
    while True:
        dt_ms = clock.tick(FPS)
        delta_time = dt_ms * 0.001
        TIMER += delta_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                pygame.mixer.quit()
                exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    menu()
                    mouse_visible = not mouse_visible
                    mouse_grab = not mouse_grab
                    pygame.mouse.set_visible(mouse_visible)
                    pygame.event.set_grab(mouse_grab)
                
                if event.key == pygame.K_f:
                    if last_sprayed >= spray_cooldown:
                        col = random.choice(glowstick_colors)
                        glowstick_tex = GLOWSTICK_TEXTURE.copy()
                        glowstick_tex.fill(col, special_flags=pygame.BLEND_RGBA_MULT)
                        SPRITES.append({'x': player_x, 'y': player_y, 'texture': glowstick_tex})
                        last_sprayed = 0

            if event.type == pygame.WINDOWFOCUSLOST:
                menu()
                mouse_visible = not mouse_visible
                mouse_grab = not mouse_grab
                pygame.mouse.set_visible(mouse_visible)
                pygame.event.set_grab(mouse_grab)

        handle_random_sounds()
        draw_scene()
        player_controller(delta_time)

        patroller.update(delta_time)
        if patroller.distance_to_player <= MAX_VIEW_DISTANCE:
            draw_sprites([patroller.as_sprite()])

        for i in ITEMS:
            i.update(delta_time)

        if last_sprayed < spray_cooldown:
            last_sprayed += delta_time
        
        pygame.display.update()

#region Buttons and Main Menu
def quit_func():
    global PLAYING
    if not PLAYING:
        pygame.quit()
        pygame.mixer.quit()
        exit(0)
    else:
        PLAYING = False
        menu()

def respawn_func():
    global player_x, player_y
    player_x, player_y = player_spawn
    main()

def menu():
    global WIDTH, HEIGHT
    heartbeat_channel.stop()

    menu_color = (192, 192, 192)
    color = (128, 128, 128)
    hover_color = (96, 96, 96)
    button_font = pygame.font.SysFont('Garamond', 48)

    click_sound = pygame.mixer.Sound('assets/click.wav')
    click_sound.set_volume(2)
    hover_sound = pygame.mixer.Sound('assets/hover.wav')
    hover_sound.set_volume(0.25)

    start_button_args = {
        'text': 'PLAY' if not PLAYING else 'CONTINUE',
        'font': button_font,
        'call_on_release': True,
        'hover_color': hover_color,
        'click_sound': click_sound,
        'hover_sound': hover_sound,
    }
    start_button_rect = pygame.Rect(int(WIDTH*0.5-196), 128, 392, 128)
    start_button = Button(start_button_rect, color, main, **start_button_args)
    start_button.rect.center = (int(WIDTH*0.5), int(HEIGHT*0.4))
    
    size_button_args = {
        'text': f'SIZE: {len(world)-1}',
        'font': button_font,
        'call_on_release': True,
        'hover_color': hover_color,
        'click_sound': click_sound,
        'hover_sound': hover_sound,
    }
    size_button_rect = pygame.Rect(int(WIDTH*0.5-196), 128, 392, 128)
    size_button = Button(size_button_rect, color, create_world, **size_button_args)
    size_button.rect.center = (int(WIDTH*0.5), int(HEIGHT*0.6))
    
    respawn_button_args = {
        'text': 'RESPAWN',
        'font': button_font,
        'call_on_release': True,
        'hover_color': hover_color,
        'click_sound': click_sound,
        'hover_sound': hover_sound,
    }
    respawn_button_rect = pygame.Rect(int(WIDTH*0.5-196), 128, 392, 128)
    respawn_button = Button(respawn_button_rect, color, respawn_func, **respawn_button_args)
    respawn_button.rect.center = (int(WIDTH*0.5), int(HEIGHT*0.6))

    quit_button_args = {
        'text': 'QUIT' if not PLAYING else 'MAIN MENU',
        'font': button_font,
        'call_on_release': True,
        'hover_color': hover_color,
        'click_sound': click_sound,
        'hover_sound': hover_sound,
    }
    quit_button_rect = pygame.Rect(int(WIDTH*0.5-196), 128, 392, 128)
    quit_button = Button(quit_button_rect, color, quit_func, **quit_button_args)
    quit_button.rect.center = (int(WIDTH*0.5), int(HEIGHT*0.8))

    menu_font = pygame.font.SysFont('Garamond', 128)
    menu_title = 'The Bob l\'éponge'
    menu_text = menu_font.render(menu_title, True, menu_color)

    background_channel.play(background_sound, 999999999)

    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    while True:
        if not PLAYING:
            screen.blit(pygame.transform.scale(BG_IMAGE, screen.get_size()), (0, 0))
        else:
            draw_scene()
        screen.blit(menu_text, (int(WIDTH*0.5 - menu_text.get_width()*0.5), 64))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                pygame.mixer.quit()
                exit(0)
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                main()

            start_button.check_event(event)
            if PLAYING:
                respawn_button.check_event(event)
            else: size_button.check_event(event)
            quit_button.check_event(event)

        start_button.update(screen)
        if PLAYING:
            respawn_button.update(screen)
        else:
            size_button.text = button_font.render(f'SIZE {cur_size}', True, pygame.Color("white"))
            size_button.update(screen)

        quit_button.update(screen)
        pygame.display.update()

#endregion

menu()