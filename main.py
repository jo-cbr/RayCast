from pygame_button import Button
from maze_generator import *
from collections import OrderedDict
from assets import *
from constants import *

#pygame.init()
clock = pygame.time.Clock()

cur_size = 32
world = wilsons_maze(cur_size, cur_size, 6)

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
end_pos, start_pos = set_spawn_and_end()

TIMER = 0

column_cache = OrderedDict()
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

#region Draw Funcs
def draw_scene(screen, h, w, ray_data, timer, player):
    screen.fill((0, 0, 0))
    draw_ray_data(ray_data, h, w, player)
    draw_sprites(SPRITES, player)
    draw_energy(screen, h, w, player.energy)
    draw_timer(screen, h, w, timer)
    draw_fps(screen, h, w, clock)
    screen.blit(VIGNETTE_SURF, (0, 0))

def draw_energy(screen, h, w, player_energy):
    c = int(255*(player_energy/100))
    color = (255, c, c)
    energy_rect = pygame.Rect(int(w*0.02), int(h*0.02), int(w*0.2*(player_energy/100)), int(h*0.03))
    bg_rect = pygame.Rect(int(w*0.02), int(h*0.02), int(w*0.2), int(h*0.03))
    pygame.draw.rect(screen, (92, 92, 92), bg_rect)
    pygame.draw.rect(screen, color, energy_rect)

def draw_fps(screen, h, w, clock):
    text = f'{clock.get_fps():.0f} FPS'
    text_rect = HUD_FONT.render(text, True, (128,128,128))
    screen.blit(text_rect, (w - text_rect.get_width() - 10, 10))

def draw_timer(screen, h, w, timer):
    minutes = timer//60
    seconds = timer%60
    text = f'{int(minutes):02}:{round(seconds):02}'
    timer_rect = HUD_FONT.render(text, True, (128,128,128))
    pos = (w//2-timer_rect.get_width()//2, h - 1.2*timer_rect.get_height())
    screen.blit(timer_rect, pos)

def draw_ray_data(ray_data, h, w, player):
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
        result = draw_ray(h, w, int(wall_height), screen_x, distance, side, grid_value, text_x, texture, player)
        if result:
            ray_blits.append(result)

    if ray_blits:
        screen.blits(ray_blits)

def draw_ray(h, w, wall_height, screen_x, distance, side, grid_value, texture_x, texture, player):
    final_x = screen_x + player.bob_offset_x
    if not 0 <= final_x < w:
        return

    if wall_height <= 0:
        return

    if distance >= MAX_DISTANCE:
        return


    target_height = min(max(1, wall_height), h*5)
    target_height = (target_height // QUANTIZE_HEIGHT) * QUANTIZE_HEIGHT
    
    half_h = target_height // 2

    top_y = int(center_y - half_h + player.bob_offset_y + player.cam_pitch)


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

def draw_sprites(sprites, player):
    if len(sprites) == 0:
        return

    dir_x = math.cos(player.angle)
    dir_y = math.sin(player.angle)
    plane_x = -dir_y * math.tan(player.half_fov)
    plane_y = dir_x * math.tan(player.half_fov)

    det = plane_x * dir_y - dir_x * plane_y
    inv_det = 1 / det

    blits = []
    spacing_factor = 8

    # Sprites nach Distanz sortieren
    sprites.sort(key = lambda s: (s['x']-player.x)**2 + (s['y']-player.y)**2, reverse=True)
    for sprite in sprites:
        sprite_x = sprite['x'] - player.x
        sprite_y = sprite['y'] - player.y

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
        
        wall_bottom_y = int(center_y + proj_wall_h//2 + player.cam_pitch + player.bob_offset_y)
        if wall_bottom_y - sprite_height > HEIGHT:
            continue
        elif wall_bottom_y + sprite_height < 0:
            continue

        draw_start_y = wall_bottom_y - sprite_height
        
        draw_start_x = -sprite_width // 2 + sprite_screen_x
        if draw_start_x < -sprite_width: draw_start_x = 0
        draw_end_x = sprite_width // 2 + sprite_screen_x - spacing_factor
        if draw_end_x >= WIDTH: draw_end_x = WIDTH - 1

        scaled_texture = pygame.transform.scale(texture, (sprite_width, sprite_height))
        for stripe in range(draw_start_x, draw_end_x):
            if stripe < 0 or stripe > WIDTH: continue
            if transform_y < Z_BUFFER[stripe]:
                tex_x = min(int((stripe - draw_start_x) * scaled_texture.get_width() / sprite_width), scaled_texture.get_width()-10)
                column = scaled_texture.subsurface((tex_x, 0, spacing_factor, sprite_height))

                blits.append((column, (stripe, draw_start_y)))

    if len(blits) > 0:
        screen.blits(blits)

#endregion
#region Ray Cast Funcs
def cast_rays(world, raystep, w, player):
    ray_data = []
    map_x = int(player.x)
    map_y = int(player.y)

    cos_vals = []
    sin_vals = []
    cos_corrections = []

    cur_size = len(world)-1

    for idx, i in enumerate(range(0, w, raystep)):
        ray_angle = player.angle - player.half_fov + (i/w) * player.fov
        cos_vals.append(math.cos(player.angle - player.fov*0.5 + (i/w) * player.fov))
        sin_vals.append(math.sin(player.angle - player.fov*0.5 + (i/w) * player.fov))
        cos_corrections.append(math.cos(ray_angle - player.angle))

    for idx, i in enumerate(range(0, w, raystep)):
        dir_x = cos_vals[idx]
        dir_y = sin_vals[idx]
        cos_correction = cos_corrections[idx]
        data = cast_single_ray(i, map_x, map_y, dir_x, dir_y, cos_correction, player, world, cur_size)
        ray_data.append(data)
    return ray_data

def cast_single_ray(i, map_x, map_y, dir_x, dir_y, cos_correction, player, world, cur_size = len(world)-1):
    global Z_BUFFER
    # Strecke pro Spalte
    delta_distance_x = abs(1 / dir_x) if dir_x != 0 else 1e30
    delta_distance_y = abs(1 / dir_y) if dir_y != 0 else 1e30

    side = 0

    # Entfernung zur nähsten Spalte
    if dir_x < 0: # nächster schnittpunkt liegt rechts
        side_dist_x = (player.x - map_x) * delta_distance_x
        step_x = -1
    else: # links
        side_dist_x = (map_x + 1 - player.x) * delta_distance_x
        step_x = 1
    if dir_y < 0:
        step_y = -1
        side_dist_y = (player.y - map_y) * delta_distance_y
    else:
        step_y = 1
        side_dist_y = (map_y + 1.0 - player.y) * delta_distance_y

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

        if map_x < 0 or map_y < 0 or map_x >= cur_size or map_y >= cur_size:
            raw_dist = min(raw_dist, MAX_DISTANCE)
            break

        if 0 <= map_x < cur_size and 0 <= map_y < cur_size:
            if grid_value != 0:
                hit = True
        else:
            # außerhalb: clamp
            raw_dist = min(raw_dist, MAX_DISTANCE)
            hit = True

    perp_distance = max(raw_dist * cos_correction, 0.01)
    if side == 0:
        wall_coord = player.y + raw_dist * dir_y
    else:
        wall_coord = player.x + raw_dist * dir_x

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
#region PlayerController
class PlayerController:
    def __init__(self, world, spawn, screen_h, screen_w, footstep_channel, exhausted_channel):
        self.world = world
        self.sh = screen_h
        self.sw = screen_w

        self.spawnpos = spawn[0] + 0.5, spawn[1] + 0.5
        self.y, self.x = self.spawnpos[0], self.spawnpos[1]

        self.fov = math.radians(60)
        self.base_fov = self.fov
        self.half_fov = self.fov / 2
        self.min_fov = self.fov * 0.95
        self.dynamic_fov_mult = 0.5

        self.angle = math.radians(0)
        self.move_speed = 1.0
        self.strafe_speed = 0.75
        self.rot_speed = 45

        self.energy = 100
        self.energy_loss_factor = 12 * max(128/(len(self.world)-1), 4)
        self.energy_gain_factor = 5

        self.bob_offset_x = self.bob_offset_y = 0
        self.view_bob_frequency = 1
        self.view_bob_amplitude = 1

        self.cam_pitch = 0

        self.footstep_channel = footstep_channel
        self.exhausted_channel = exhausted_channel

    def update(self, deltatime):
        next_x, next_y = self.x, self.y
        forward = strafe = 0
        walk_cycle = 0
        moving = False

        if pygame.event.get_grab():
            mouse_x, mouse_y = pygame.mouse.get_rel()
            if mouse_x != 0:
                norm_mouse_x = mouse_x/self.sw
                self.angle += norm_mouse_x * self.rot_speed * deltatime
            if mouse_y != 0:
                self.cam_pitch -= mouse_y * self.rot_speed * deltatime
                self.cam_pitch = min(max(self.cam_pitch, -self.sh), self.sh)

            if pygame.mouse.get_just_released()[0]:
                dir_x = math.cos(self.angle)
                dir_y = math.sin(self.angle)
                cos_correction = math.cos(0)
                result = cast_single_ray(int(self.sw*0.5),int(self.x), int(self.y), dir_x, dir_y, cos_correction, self, self.world, len(self.world)-1)
                if result[4] == 2 and result[2] <= 1.5:
                    menu(False)
                if result[4] == 4 and result[2] <= 1.5:
                    world[result[6]] = 5
                    item_sound_channel.play(gong_sound)
                    self.spawnpos = int(self.x) + 0.5, int(self.y) + 0.5

        if forward < 1.5 and self.energy < 100:
            self.energy += self.energy_gain_factor * deltatime
            self.energy = min(self.energy, 100)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]:
            if keys[pygame.K_LSHIFT]:
                forward = 0.75
            elif keys[pygame.K_LCTRL] and not self.exhausted_channel.get_busy():
                if self.energy > 0:
                    forward = 2
                    self.energy -= self.energy_loss_factor * deltatime
                    if self.energy <= 0:
                        self.energy = 0
                        self.exhausted_channel.play(exhausted)
                if self.fov > self.min_fov:
                    self.fov -= (self.fov - self.min_fov) * self.dynamic_fov_mult * deltatime
            else:
                if self.fov < self.base_fov:
                    self.fov += (self.base_fov - self.fov) * self.dynamic_fov_mult * deltatime
                forward = 1

        if keys[pygame.K_s]:
            forward = -0.5
        if keys[pygame.K_a]:
            strafe = -1
        if keys[pygame.K_d]:
            strafe = 1

        next_x += math.cos(self.angle) * self.move_speed * forward * deltatime
        next_y += math.sin(self.angle) * self.move_speed * forward * deltatime
        next_x += -math.sin(self.angle) * self.strafe_speed * strafe * deltatime
        next_y += math.cos(self.angle) * self.strafe_speed * strafe * deltatime

        # Potentielle Distanz berechnen. Wird verworfen falls is_empty() auf False läuft
        distance = (next_x - self.x)**2 + (next_y - self.y)**2

        if next_x != self.x:
            if self.check_distance_to_wall(next_x, self.y):
                if self.is_empty(next_x, self.y):
                    self.x = next_x
                    moving = True
        if next_y != self.y:
            if self.check_distance_to_wall(self.x, next_y):
                if self.is_empty(self.x, next_y):
                    self.y = next_y
                    moving = True

        if distance > 0 and moving:
            walk_cycle += distance
            walk_cycle %= math.pi*2
        else:
            walk_cycle -= 0.25
            walk_cycle = max(walk_cycle, 0)

        self.bob_offset_x = math.cos(walk_cycle * self.view_bob_frequency) * self.view_bob_amplitude * forward
        self.bob_offset_y = self.view_bob_frequency * math.sin(walk_cycle * self.view_bob_frequency) * self.view_bob_amplitude * forward

        if moving and not self.footstep_channel.get_busy():
            s = self.footstep_channel.get_sound()
            if forward == 1.5:
                if s != footstep_sprint:
                    self.footstep_channel.stop()
                self.footstep_channel.play(footstep_sprint)
            elif forward >= 1:
                if s != footstep_reg:
                    self.footstep_channel.stop()
                self.footstep_channel.play(footstep_reg)
        elif not moving and self.footstep_channel.get_busy():
            self.footstep_channel.fadeout(100)
            self.footstep_channel.stop()

    def check_distance_to_wall(self, px, py, margin = 0.15):
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

    def is_empty(self, px, py):
        grid_x = int(px)
        grid_y = int(py)
        if 0 <= grid_y < len(world) and 0 <= grid_x < len(world[0]):
            return world[grid_y][grid_x] == 0
        return False
#endregion
#region Patrolling Enemy
class Patroller:
    def __init__(self, world):
        self.world = world
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
        height = width = len(self.world)-1
        spawns = []
        for y in range(height-1):
            if self.world[y][width-2] == 0:
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

        if self.world[ty, tx] == 0:
            return [(ty, tx)]
        
        dy, dx = self.get_direction_vector(self.cur_dir)
        ty, tx = int(self.y) + dy, int(self.x) + dx
        if self.world[ty, tx] == 0:
            return [(ty, tx)]
        
        right_dir = self.directions[(idx + 3) % 4]
        dy, dx = self.get_direction_vector(right_dir)
        ty, tx = int(self.y) + dy, int(self.x) + dx
        if self.world[ty, tx] == 0:
            return [(ty, tx)]
        
        back_dir = self.directions[(idx + 2) % 4]
        dy, dx = self.get_direction_vector(back_dir)
        ty, tx = int(self.y) + dy, int(self.x) + dx
        if self.world[ty, tx] == 0:
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

    def can_see_player(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        if dist > self.view_distance:
            return False

        dir_map = {'North': (1,0), 'South': (-1,0), 'East': (0,1), 'West': (0,-1)}
        dir_vector = dir_map[self.cur_dir]

        angle = math.acos((dx*dir_vector[1] + dy*dir_vector[0]) / (dist+1e-6))
        if angle > self.view_angle:
            return False

        if not self.has_line_of_sight(self.x, self.y, player.x, player.y, self.world):
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
        if all(0 <= cy < len(self.world) and 0 <= cx < len(self.world[0]) and self.world[cy][cx] == 0 for cy, cx in cells_x):
            self.x = new_x
        else:
            step_x = 0

        cells_y = [
            (int(new_y - radius), int(self.x - radius)),
            (int(new_y - radius), int(self.x + radius)),
            (int(new_y + radius), int(self.x - radius)),
            (int(new_y + radius), int(self.x + radius)),
        ]
        if all(len(self.world) > cy >= 0 == self.world[cy][cx] and 0 <= cx < len(self.world[0]) for cy, cx in cells_y):
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

    def update(self, deltatime, player):
        self.distance_to_player = math.sqrt((player.x-self.x) ** 2 + (player.y-self.y) ** 2)
        if self.distance_to_player <= MAX_VIEW_DISTANCE:
            draw_sprites([self.as_sprite()], player)
        if not self.active:
            return
        if self.distance_to_player < 8:
            path_to_player = a_star(self.world, (int(self.y), int(self.x)), (int(player.y), int(player.x)))
        else:
            path_to_player = []
        close_to_player = False

        # Kill Player
        if self.distance_to_player < 0.3:
            random_sound_channel.play(death_sound)
            heartbeat_channel.fadeout(50)
            self.y, self.x = self.get_start_pos()
            player.y, player.x = player.spawnpos

        # Fallback
        if path_to_player is None:
            return
        
        if self.mode == 'Patrolling':
            if not self.current_path:
                self.current_path = self.get_target_pos()
            if self.distance_to_player < 8:
                # Spieler kann gehört werden wenn zu nah, len statt distance sodass es nicht durch wände geht
                if self.can_see_player(player) or 0 < (len(path_to_player) < 5 and footstep_channel.get_busy()):
                    self.mode = 'Chasing'
                    self.player_seen_pos = (int(player.y), int(player.x))
                    self.current_path = a_star(self.world, (int(self.y), int(self.x)), self.player_seen_pos)
                    self.view_angle = math.pi/3

        if self.mode == 'Chasing':
            self.player_seen_pos = (int(player.y), int(player.x))
            if len(path_to_player) > 1:
                path_to_player.pop(0)

            # Logik für verschiedene Szenarien
            if self.distance_to_player > self.view_distance or (self.distance_to_player > self.view_distance/2 and not self.can_see_player(player)):
                self.mode = 'Patrolling'
                self.view_angle = math.pi/4
            if self.can_see_player(player):
                if self.distance_to_player < 2:
                    close_to_player = True
                    self.current_path = [(player.y, player.x)]
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
        dx_to_player = player.x - self.x
        dy_to_player = player.y - self.y

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
BUFFS = []
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
            ['speed_boost', 20, self.speed_up_player, self.slow_down_player, SPEED_BOOST_TEXTURE],
            ['crystal_ball', 4, self.show_path, None, CRYSTAL_BALL_TEXTURE]
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
        global player
        player.move_speed = 1.25
    def slow_down_player(self):
        global player
        player.move_speed = 1

    def show_path(self):
        path = a_star(world, (int(player.y), int(player.x)), end_pos)
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
                BUFFS.remove(self.name)
                if self.name not in BUFFS:
                    if self.revert_ability_func is not None:
                        self.revert_ability_func()
                ITEMS.remove(self)
            return
        else:
            distance_to_player = (player.x-self.x) ** 2 + (player.y-self.y) ** 2
            if distance_to_player > 1:
                return
            
            if distance_to_player < 0.1:
                if self.ability_func is not None:
                    item_sound_channel.play(gong_sound)
                    self.ability_func()
                    self.ability_used = True
                    BUFFS.append(self.name)
                    SPRITES.remove(self.sprite_dict)

def spawn_items():
    empty_cells = [(y, x) for y in range(cur_size) for x in range(cur_size) if world[y, x] == 0]
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
        if random.randint(1, 10) > 8:
            item_pos = pos[0]+0.5, pos[1]+0.5
            item = Item(item_pos)
            ITEMS.append(item)
#endregion
#region Worldgeneration
def place_checkpoints(start, end):
    empty_cells = [(y, x) for y in range(cur_size) for x in range(cur_size) if world[y, x] == 0]
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
    global world, cur_size
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
#region Gameloop
patroller = Patroller(world)
player = PlayerController(world, start_pos, HEIGHT, WIDTH, footstep_channel, player_sound_channel)

def main(new_game):
    global cur_size, world, TIMER, SPRITES, patroller, end_pos, player, start_pos
    
    mouse_visible = False
    mouse_grab = True
    pygame.mouse.set_visible(mouse_visible)
    pygame.event.set_grab(mouse_grab)

    glowstick_cooldown = 1.0
    last_thrown = 1.0
    
    # World Creation and Setup
    if new_game:
        TIMER = 0
        while True:
            loading_screen('Generating Maze...')
            world = wilsons_maze(cur_size, cur_size, cur_size//8)
            cur_size = len(world) - 1
            # Pathfind weg erstellen
            end_pos, start_pos = set_spawn_and_end()
            maze_path = a_star(world, start_pos, end_pos)
            if maze_path is None:
                continue
            if len(maze_path) > cur_size:
                break

        if cur_size > 16:
            loading_screen('Placing Checkpoints...')
            place_checkpoints(start_pos, end_pos)

        SPRITES=[]
        loading_screen('Spawning Enemies...')
        patroller = Patroller(world)

        loading_screen('Placing Items...')
        spawn_items()

        player = PlayerController(world, start_pos, HEIGHT, WIDTH, footstep_channel, player_sound_channel)

    # Fallback
    if patroller is None:
        patroller = Patroller(world)

    clock.tick(FPS)
    while True:
        dt_ms = clock.tick(FPS)
        deltatime = dt_ms * 0.001
        TIMER += deltatime

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                pygame.mixer.quit()
                exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    menu(True)
                    mouse_visible = not mouse_visible
                    mouse_grab = not mouse_grab
                    pygame.mouse.set_visible(mouse_visible)
                    pygame.event.set_grab(mouse_grab)
                
                if event.key == pygame.K_f:
                    if last_thrown >= glowstick_cooldown:
                        col = random.choice(glowstick_colors)
                        glowstick_tex = GLOWSTICK_TEXTURE.copy()
                        glowstick_tex.fill(col, special_flags=pygame.BLEND_RGBA_MULT)
                        SPRITES.append({'x': player.x, 'y': player.y, 'texture': glowstick_tex})
                        last_thrown = 0

            if event.type == pygame.WINDOWFOCUSLOST:
                menu(True)
                mouse_visible = not mouse_visible
                mouse_grab = not mouse_grab
                pygame.mouse.set_visible(mouse_visible)
                pygame.event.set_grab(mouse_grab)

        handle_random_sounds()
        ray_data = cast_rays(world, RAY_STEP, WIDTH, player)
        draw_scene(screen, HEIGHT, WIDTH, ray_data, TIMER, player)
        player.update(deltatime)

        patroller.update(deltatime, player)
        for i in ITEMS:
            i.update(deltatime)

        if last_thrown < glowstick_cooldown:
            last_thrown += deltatime
        
        pygame.display.update()
#endregion
#region Buttons and Main Menu
def quit_func(playing):
    if not playing:
        pygame.quit()
        pygame.mixer.quit()
        exit(0)
    else:
        menu(False)

def respawn_func():
    player.x, player.y = player.spawnpos
    main(False)

def menu(playing):
    global WIDTH, HEIGHT
    heartbeat_channel.stop()

    menu_color = (192, 192, 192)
    color = (128, 128, 128)
    hover_color = (96, 96, 96)
    
    start_button_args = {
        'text': 'PLAY' if not playing else 'CONTINUE',
        'font': button_font,
        'call_on_release': True,
        'hover_color': hover_color,
        'click_sound': click_sound,
        'hover_sound': hover_sound,
    }
    start_new_game = lambda: main(True)
    start_button_rect = pygame.Rect(int(WIDTH*0.5-196), 128, 392, 128)
    start_button = Button(start_button_rect, color, start_new_game, **start_button_args)
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
        'text': 'QUIT' if not playing else 'MAIN MENU',
        'font': button_font,
        'call_on_release': True,
        'hover_color': hover_color,
        'click_sound': click_sound,
        'hover_sound': hover_sound,
    }
    quit_func_helper = lambda: quit_func(playing)
    quit_button_rect = pygame.Rect(int(WIDTH*0.5-196), 128, 392, 128)
    quit_button = Button(quit_button_rect, color, quit_func_helper, **quit_button_args)
    quit_button.rect.center = (int(WIDTH*0.5), int(HEIGHT*0.8))

    menu_font = pygame.font.SysFont('Garamond', 128)
    menu_title = 'The Bob l\'éponge'
    menu_text = menu_font.render(menu_title, True, menu_color)

    background_channel.play(background_sound, 999999999)

    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)

    while True:
        if not playing:
            screen.blit(pygame.transform.scale(BG_IMAGE, screen.get_size()), (0, 0))
        else:

            ray_data = cast_rays(world, RAY_STEP, WIDTH, player)
            draw_scene(screen, HEIGHT, WIDTH, ray_data, TIMER, player)
        screen.blit(menu_text, (int(WIDTH*0.5 - menu_text.get_width()*0.5), 64))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                pygame.mixer.quit()
                exit(0)
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                main(False)

            start_button.check_event(event)
            if playing:
                respawn_button.check_event(event)
            else: size_button.check_event(event)
            quit_button.check_event(event)

        start_button.update(screen)
        if playing:
            respawn_button.update(screen)
        else:
            size_button.text = button_font.render(f'SIZE {cur_size}', True, pygame.Color("white"))
            size_button.update(screen)

        quit_button.update(screen)
        pygame.display.update()

#endregion

menu(False)