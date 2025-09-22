import pygame
from state import *
from textures import *
from sounds import *

# region Items
ITEMS = []
ITEM_FONT = pygame.font.SysFont('Garamond', 48)
active_buffs = []

class Item:
    def __init__(self, pos):
        self.get_random_type()
        self.y, self.x = pos
        self.time_passed = 0
        self.ability_used = False
        self.sprite_dict = {'type':'Item', 'x': self.x, 'y': self.y, 'texture': self.texture}
        SPRITES.append(self.sprite_dict)

    def get_random_type(self):
        types = [
            ['torch', 15, self.increase_max_view_dist, self.decrease_max_view_dist, TORCH_TEXTURE,
             'Let there be Light'],
            ['cross', 30, self.set_patroller_inactive, self.set_patroller_active, CROSS_TEXTURE,
             'The Lord is my Shepherd'],
            ['speed_boost', 10, self.speed_up_player, self.slow_down_player, SPEED_BOOST_TEXTURE, ''],
            ['crystal_ball', 4, self.show_path, None, CRYSTAL_BALL_TEXTURE, 'All shall be revealed']
        ]

        random_type = random.choice(types)

        self.name = random_type[0]
        self.duration = random_type[1]
        self.ability_func = random_type[2]
        self.revert_ability_func = random_type[3]
        self.texture = pygame.transform.scale_by(random_type[4], 20)
        self.text = ITEM_FONT.render(random_type[5], True, (128, 128, 128))
        self.text_rect = self.text.get_rect()
        self.text_rect.center = (WIDTH // 2, center_y)

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
        player_speed_mult = 1.5

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
            SPRITES.append({'type':'Glowstick', 'x': pos[1] + 0.5, 'y': pos[0] + 0.5, 'texture': glowstick_tex})

    def update(self, deltatime):
        if self.ability_used:
            self.time_passed += deltatime
            if self.time_passed <= 3:
                self.text.set_alpha(255 * (1 - (self.time_passed / 3)))
                screen.blit(self.text, self.text_rect)
            if self.time_passed >= self.duration:
                ITEMS.remove(self)
                if self.name in active_buffs:
                    return
                if self.revert_ability_func is not None:
                    self.revert_ability_func()
                self.time_passed = 0
                self.ability_used = False
            return
        else:
            distance_to_player = (player_x - self.x) ** 2 + (player_y - self.y) ** 2
            if distance_to_player > 1:
                return

            if distance_to_player < 0.1:
                if self.ability_func is not None:
                    self.ability_func()
                    item_channel.play(gong_sound)
                    active_buffs.append(self.name)
                    self.ability_used = True
                    if self.sprite_dict in SPRITES:
                        SPRITES.remove(self.sprite_dict)


def spawn_items():
    empty_cells = get_empty_cells(world)
    dead_ends = []
    for pos in empty_cells:
        r, c = pos
        # Prüfen ob Sackgasse
        if ((world[r - 1, c] == 0 and world[r + 1, c] == 1 and world[r, c - 1] == 1 and world[r, c + 1] == 1) or
                (world[r - 1, c] == 1 and world[r + 1, c] == 0 and world[r, c - 1] == 1 and world[r, c + 1] == 1) or
                (world[r - 1, c] == 1 and world[r + 1, c] == 1 and world[r, c - 1] == 0 and world[r, c + 1] == 1) or
                (world[r - 1, c] == 1 and world[r + 1, c] == 1 and world[r, c - 1] == 1 and world[r, c + 1] == 0)):
            dead_ends.append((r, c))

    random.shuffle(dead_ends)
    for pos in dead_ends:
        if random.randint(1, 10) > 0:
            item_pos = pos[0] + 0.5, pos[1] + 0.5
            item = Item(item_pos)
            ITEMS.append(item)
# endregion