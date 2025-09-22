import pygame, random
from state import *

pygame.mixer.init()

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