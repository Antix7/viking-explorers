from math import *
import pygame as pg
from pygame.constants import QUIT

MAP_SCALE = 2400*18/pi #[px/rad]
MAP_LAT_START = (pi/2)*(4/9)
MAP_LON_START = -(pi/2)*(7/9)

def project_spherical(latitude, longitude):
    x = MAP_SCALE * (longitude-MAP_LON_START)
    y = MAP_SCALE * (latitude-MAP_LAT_START)
    return x, y

pg.init()
window = pg.display.set_mode((1000, 500))
game_map = pg.transform.scale_by(pg.image.load("data/game_map.jpg").convert(), 1/25)
map_height = game_map.get_rect().height

lat = (59+48/60+53.23/3600)*(pi/180)
lon = -(43 + 35/60 + 08.25/3600)*(pi/180)



window.blit(game_map, (0, 0))
x, y = project_spherical(lat, lon)
x /= 25; y /= 25
print(x, y)
print(map_height)
pg.draw.circle(window, "red", (x, map_height-y), 3)
pg.display.flip()
run = True
while run:
    for event in pg.event.get():
        if event.type == QUIT:
            run = False

pg.quit()