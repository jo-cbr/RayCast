import random
from constants import *

# Textures
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


# Sounds
pygame.mixer.init()


background_channel = pygame.mixer.Channel(0)

background_sound = pygame.mixer.Sound('assets/sounds/background_sound.mp3')
background_sound.set_volume(0.1)

footstep_channel = pygame.mixer.Channel(1)
footstep_channel.set_volume(0.1)

footstep_reg = pygame.mixer.Sound('assets/sounds/footsteps_reg.mp3')
footstep_reg.set_volume(0.1)
footstep_sprint = pygame.mixer.Sound('assets/sounds/footsteps_sprint.mp3')
footstep_sprint.set_volume(0.2)

random_sound_channel = pygame.mixer.Channel(2)
random_sound_channel.set_source_location(180, 5)
wind_sound = pygame.mixer.Sound('assets/sounds/wind_sound.mp3')
wind_sound.set_volume(1.1)
intense_sound = pygame.mixer.Sound('assets/sounds/intense_suspense.mp3')
intense_sound.set_volume(0.2)
footsteps_behind = pygame.mixer.Sound('assets/sounds/footsteps_behind.mp3')
humming = pygame.mixer.Sound('assets/sounds/humming.mp3')
ghost_sound = pygame.mixer.Sound('assets/sounds/ghost_sound.mp3')
branch_cracking = pygame.mixer.Sound('assets/sounds/cracking_sound.mp3')
branch_cracking.set_volume(0.8)
death_sound = pygame.mixer.Sound('assets/sounds/death_beep.mp3')
death_sound.set_volume(0.7)

heartbeat_channel = pygame.mixer.Channel(3)
heartbeat_slow = pygame.mixer.Sound('assets/sounds/heartbeat_slow.mp3')
heartbeat_medium = pygame.mixer.Sound('assets/sounds/heartbeat_medium.mp3')
heartbeat_fast = pygame.mixer.Sound('assets/sounds/heartbeat_fast.mp3')

player_sound_channel = pygame.mixer.Channel(4)
exhausted = pygame.mixer.Sound('assets/sounds/exhausted.mp3')
exhausted.set_volume(2)

item_sound_channel = pygame.mixer.Channel(5)
gong_sound = pygame.mixer.Sound('assets/sounds/gong_sound.mp3')

click_sound = pygame.mixer.Sound('assets/sounds/click.wav')
click_sound.set_volume(1)
hover_sound = pygame.mixer.Sound('assets/sounds/hover.wav')
hover_sound.set_volume(0.25)

def handle_random_sounds():
    rare_sounds = [wind_sound, footsteps_behind, intense_sound, branch_cracking, humming, ghost_sound]
    if random.random() > 0.9999 and not random_sound_channel.get_busy():
        random_sound_channel.play(random.choice(rare_sounds))