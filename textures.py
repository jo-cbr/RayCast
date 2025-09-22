from state import *

pygame.init()

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