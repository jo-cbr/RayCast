import pygame, math
from pygame_button import Button
from maze_generator import *

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
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN, vsync=True)
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
        (width-2, y) for y in range(height-2)
        if (world[y][width-2] == 0) and
        ((world[y-1][width-2] == 0 and world[y+1][width-2] != 0) or
        (world[y+1][width-2] == 0 and world[y-11][width-2] != 0))
    ]

    # Punkte Links im Labyrinth
    spawn_points = [(1, y) for y in range(height-1) if world[y][1] == 0]

    p1 = random.choice(goal_points)
    world[p1] = 2
    
    p2 = random.choice(spawn_points)

    return p1, p2

player_spawn = player_x, player_y = set_spawn_and_end()

player_energy = 100
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
wind_sound.set_volume(1)
intense_sound = pygame.mixer.Sound('assets/intense_suspense.mp3')
intense_sound.set_volume(0.1)
footsteps_behind = pygame.mixer.Sound('assets/footsteps_behind.mp3')
humming = pygame.mixer.Sound('assets/humming.mp3')
ghost_sound = pygame.mixer.Sound('assets/ghost_sound.mp3')
branch_cracking = pygame.mixer.Sound('assets/cracking_sound.mp3')

player_action_channel = pygame.mixer.Channel(3)
spray_sound = pygame.mixer.Sound('assets/spray.mp3')

#endregion
PROJ_PLANE = (WIDTH / 2) / math.tan(FOV * 0.5)

#region Textures
BG_IMAGE = pygame.image.load('assets/main_background.png').convert()

WALL_TEXTURE = pygame.image.load('assets/bushwall.png').convert()
MARKED_WALL_TEXTURE = pygame.image.load('assets/marked_bushwall.png').convert()
CHECKPOINT_WALL_TEXTURE = pygame.image.load('assets/checkpoint_wall.png')
SAVED_CHECKPOINT_WALL_TEXTURE = pygame.image.load('assets/saved_checkpoint_wall.png')

WALL_TEXTURE_WIDTH, WALL_TEXTURE_HEIGHT = WALL_TEXTURE.get_size()
GLOBAL_WALL_SCALE = 1

VIGNETTE_SURF = pygame.image.load('assets/vignette.png').convert_alpha()
VIGNETTE_SURF = pygame.transform.scale(VIGNETTE_SURF, screen.get_size())

SPRAY1 = pygame.image.load('assets/animations/spray_overlay1.png').convert_alpha()
SPRAY2 = pygame.image.load('assets/animations/spray_overlay2.png').convert_alpha()
SPRAY3 = pygame.image.load('assets/animations/spray_overlay3.png').convert_alpha()
SPRAY4 = pygame.image.load('assets/animations/spray_overlay4.png').convert_alpha()
SPRAY5 = pygame.image.load('assets/animations/spray_overlay5.png').convert_alpha()
SPRAY_ANIMATION = [SPRAY1, SPRAY2, SPRAY3, SPRAY4, SPRAY5]
#endregion
column_cache = {}
CACHE_MAX_SIZE = 2048
QUANTIZE_HEIGHT = 2

RAY_STEP = 6

BRIGHTNESS_FALLOFF = 2
#region Draw Funcs
def draw_scene():
    screen.fill((0, 0, 0))
    ray_data = cast_rays()
    draw_ray_data(ray_data)
    draw_energy()
    draw_timer()
    screen.blit(VIGNETTE_SURF, (0, 0))

def draw_energy():
    c = int(255*(player_energy/100))
    color = (255, c, c)
    energy_rect = pygame.Rect(int(WIDTH*0.02), int(HEIGHT*0.02), int(WIDTH*0.2*(player_energy/100)), int(HEIGHT*0.03))
    pygame.draw.rect(screen, (128, 128, 128), pygame.Rect(int(WIDTH*0.02), int(HEIGHT*0.02), int(WIDTH*0.2), int(HEIGHT*0.03)))
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
        2: WALL_TEXTURE,
        3: MARKED_WALL_TEXTURE,
        4: CHECKPOINT_WALL_TEXTURE,
        5: SAVED_CHECKPOINT_WALL_TEXTURE,
    }
    for ray in ray_data:
        wall_height, screen_x, distance, side, grid_value, text_x, wall_pos = ray
        texture = textures[grid_value]
        draw_ray(wall_height, screen_x, distance, side, grid_value, text_x, texture)

def draw_ray(wall_height, screen_x, distance, side, grid_value, texture_x, texture):
    final_x = screen_x + bob_offset_x
    if not 0 <= final_x < WIDTH:
        return

    if wall_height <= 0:
        return

    if distance >= MAX_DISTANCE:
        return

    half_h = wall_height // 2

    top_y = int(center_y - half_h + bob_offset_y + cam_pitch)
    bottom_y = int(center_y + half_h + bob_offset_y + cam_pitch)

    texture_height = texture.get_height()

    target_height = min(max(1, bottom_y - top_y), 10*HEIGHT)
    target_height = (target_height // QUANTIZE_HEIGHT) * QUANTIZE_HEIGHT
    cache_key = (texture_x, target_height, grid_value)
    col_surf = column_cache.get(cache_key)

    if col_surf is None:
        tx = max(0, min(texture.get_width() - 1, texture_x))
        tex_col = texture.subsurface((tx, 0, 1, texture_height))
        col_surf = pygame.transform.scale(tex_col, (RAY_STEP, target_height))

        if len(column_cache) > CACHE_MAX_SIZE:
            column_cache.pop(next(iter(column_cache)))

        column_cache[cache_key] = col_surf

    screen.blit(col_surf, (final_x, top_y))

    # Helligkeit managen
    norm_distance = distance / MAX_VIEW_DISTANCE
    brightness = BRIGHTNESS_FALLOFF * (norm_distance ** 2)
    brightness = min(max(brightness, 0), 1)

    shadow_color = brightness * 48 + (0 if side else 8)

    rect = pygame.Rect(final_x, top_y, RAY_STEP, target_height)

    # Legt finales "Schatten Layer" über Surface
    if grid_value == 2:
        screen.fill((64, 0, 0), rect, special_flags=pygame.BLEND_ADD)
    screen.fill((shadow_color, shadow_color, shadow_color), rect, special_flags=pygame.BLEND_SUB)
#endregion

#region Ray Cast Funcs
def cast_rays():
    ray_data = []
    half_fov = FOV * 0.5
    map_x = int(player_x)
    map_y = int(player_y)

    cos_vals = [math.cos(player_angle - FOV*0.5 + (i/WIDTH) * FOV) for i in range(0, WIDTH, RAY_STEP)]
    sin_vals = [math.sin(player_angle - FOV*0.5 + (i/WIDTH) * FOV) for i in range(0, WIDTH, RAY_STEP)]

    for idx, i in enumerate(range(0, WIDTH, RAY_STEP)):
        dir_x = cos_vals[idx]
        dir_y = sin_vals[idx]
        data = cast_single_ray(i, half_fov, map_x, map_y, dir_x, dir_y)
        ray_data.append(data)
    return ray_data

def cast_single_ray(i, half_fov, map_x, map_y, dir_x, dir_y):
    global Z_BUFFER
    ray_angle = player_angle - half_fov + (i/WIDTH) * FOV

    # Strecke pro Spalte
    if dir_x == 0:
        delta_distance_x = float("inf")
    else:
        delta_distance_x =  abs( 1 / dir_x)
    if dir_y == 0:
        delta_distance_y = float("inf")
    else:
        delta_distance_y = abs(1 / dir_y)

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

        grid_value = world[map_y][map_x]
        if 0 <= map_x < GRID_WIDTH and 0 <= map_y < GRID_HEIGHT:
            if grid_value != 0:
                hit = True
        else:
            # außerhalb: clamp
            raw_dist = min(raw_dist, MAX_DISTANCE)
            hit = True

    cos_correction = math.cos(ray_angle - player_angle)
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
    wall_height = int((1.0 / perp_distance) * PROJ_PLANE * GLOBAL_WALL_SCALE)
    Z_BUFFER[i] = perp_distance

    return wall_height, i, perp_distance, side, grid_value, text_x, wall_pos
#endregion

#region Player Controller Funcs
exhausted_played = False
def player_controller(delta_time):
    # Alle globalen vars die gebraucht werden
    global player_x, player_y, player_angle, player_spawn, \
            cam_pitch, center_y, FOV, player_energy, PLAYING, \
            walk_cycle, bob_offset_y, bob_offset_x, exhausted_played

    next_x, next_y = player_x, player_y
    move_speed = 1
    strafe_speed = 0.75
    rot_speed = 30
    energy_loss_factor = 25
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
        if keys[pygame.K_LCTRL] and not exhausted_played:
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

    next_x += math.cos(player_angle) * move_speed * forward * delta_time
    next_y += math.sin(player_angle) * move_speed * forward * delta_time
    next_x += -math.sin(player_angle) * strafe_speed * strafe * delta_time
    next_y += math.cos(player_angle) * strafe_speed * strafe * delta_time

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

    # Handle footsteps (probably very fucked and inefficient but who cares it doesnt drop frames frfr)
    if moving and not footstep_channel.get_busy():
        q = footstep_channel.get_queue()
        if forward == 1.5:
            if q != footstep_sprint:
                footstep_channel.stop()
            footstep_channel.play(footstep_sprint)
        else:
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

    neighbors = [
        (gx - 1, gy, dx),  # links
        (gx + 1, gy, 1 - dx),  # rechts
        (gx, gy - 1, dy),  # oben
        (gx, gy + 1, 1 - dy) # unten
    ]
    for nx, ny, dist_frac in neighbors:
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

def handle_random_sounds():
    global random_sound_channel
    rare_sounds = [wind_sound, footsteps_behind, intense_sound, branch_cracking, humming, ghost_sound]
    if random.random() > 0.9999 and not random_sound_channel.get_busy():
        random_sound_channel.play(random.choice(rare_sounds))


#region Worldgeneration
def place_checkpoints(start, end):
    empty_cells = [(y, x) for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH) if world[x, y] == 0]
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
def main():
    global cam_pitch, player_view, PLAYING, GRID_HEIGHT, GRID_WIDTH, \
        player_x, player_y, player_spawn, world, TIMER
    mouse_visible = False
    mouse_grab = True
    pygame.mouse.set_visible(mouse_visible)
    pygame.event.set_grab(mouse_grab)
    spray_cooldown = 1.0
    last_sprayed = 1.0
    
    spray_frame = 1
    spray_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    
    if not PLAYING:
        TIMER = 0
        while True:
            loading_screen('Generating Maze...')
            world = wilsons_maze(cur_size, cur_size, 5)
            GRID_HEIGHT, GRID_WIDTH = len(world), len(world[0])
            # Pathfind weg erstellen
            start_pos, end_pos = set_spawn_and_end()
            maze_path = a_star(world, start_pos, end_pos)
            if maze_path is None:
                continue
            if len(maze_path) > cur_size:
                break

        if GRID_HEIGHT > 16:
            loading_screen('Placing Checkpoints...')
            place_checkpoints(start_pos, end_pos)

        player_spawn = player_x, player_y = start_pos[0] + 0.5, start_pos[1] + 0.5

        PLAYING = True

    test_surf = pygame.Surface((1, 8))
    test_surf.fill((255,0,0))
    clock.tick(FPS)
    print(cur_size)
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
                        player_view = cast_single_ray(int(WIDTH*0.5)-1, FOV*0.5, int(player_x), int(player_y), math.cos(player_angle), math.sin(player_angle))
                        if player_view[2] <= 2: # wenn nah genug
                            spray_y, spray_x = player_view[6]
                            if world[spray_y][spray_x] == 1:
                                player_action_channel.play(spray_sound)
                                world[spray_y][spray_x] = 3
                                spray_frame=1
                                last_sprayed = 0

        handle_random_sounds()
        draw_scene()
        player_controller(delta_time)

        if last_sprayed < spray_cooldown:
            if last_sprayed < spray_cooldown*0.5:
                spray_surf.fill((0,0,0,0))
                screen.blit(pygame.transform.scale(SPRAY_ANIMATION[spray_frame-1], (256, 256)), (WIDTH*0.5, HEIGHT-256))
                spray_frame += int(last_sprayed*5)
                spray_frame = min(spray_frame, 5)
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