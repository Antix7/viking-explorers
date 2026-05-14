from math import *
import pygame as pg
from pygame.constants import *

MAP_SCALE = 2400*18/pi #[px/rad]
MAP_LAT_START = (pi/2)*(4/9)
MAP_LON_START = -(pi/2)*(7/9)

def project_spherical(latitude, longitude):
    x = MAP_SCALE * (longitude-MAP_LON_START)
    y = MAP_SCALE * (latitude-MAP_LAT_START)
    return x, y

def get_crop_parameters(camera_x, camera_y, scaled_map_width, scaled_map_height):
    top_left_x = max(-camera_x, 0)
    top_left_y = max(-camera_y, 0)
    bottom_right_x = min(window_width-camera_x, scaled_map_width)
    bottom_right_y = min(window_height-camera_y, scaled_map_height)
    crop_rect = pg.Rect(
        top_left_x, top_left_y,
        bottom_right_x - top_left_x,
        bottom_right_y - top_left_y)
    draw_position_x = 0 if camera_x <= 0 else camera_x
    draw_position_y = 0 if camera_y <= 0 else camera_y
    print(camera_x, camera_y, scaled_map_width, scaled_map_height)
    print(crop_rect)
    return {
        "crop_rect": crop_rect,
        "draw_position_x": draw_position_x,
        "draw_position_y": draw_position_y,
    }


pg.init()

display_info = pg.display.Info()
window_width = int(display_info.current_w * 0.8)
window_height = int(display_info.current_h * 0.7)
print(window_width, window_height)

screen = pg.display.set_mode((window_width, window_height))
pg.display.set_caption("Viking Explorers")
map_image = pg.image.load("data/game_map.jpg").convert()

zoom_level = 0.1
zoom_factor = 1.2
camera_x = 0
camera_y = 0
lmb_held_down = False

run = True
while run:
    for event in pg.event.get():
        if event.type == QUIT:
            run = False

        # Zooming of the map
        if event.type == MOUSEWHEEL:
            zoom_exponent = 0
            if event.y > 0:
                zoom_exponent = 1
            elif event.y < 0:
                zoom_exponent = -1
            zoom_level *= zoom_factor**zoom_exponent
            mouse_x, mouse_y = pg.mouse.get_pos()
            camera_x = mouse_x + (camera_x - mouse_x) * (zoom_factor**zoom_exponent)
            camera_y = mouse_y + (camera_y - mouse_y) * (zoom_factor**zoom_exponent)

    # Panning of the map
    if pg.mouse.get_pressed()[0]:
        if lmb_held_down:
            mouse_dx, mouse_dy = pg.mouse.get_rel()
            camera_x += mouse_dx
            camera_y += mouse_dy
        else:
            lmb_held_down = True
            pg.mouse.get_rel()
    else:
        lmb_held_down = False

    # Drawing the map on the screen
    screen.fill((0, 0, 0))
    scaled_map = pg.transform.smoothscale_by(map_image, zoom_level)
    crop_parameters = get_crop_parameters(
        camera_x, camera_y,
        scaled_map.get_rect().width, scaled_map.get_rect().height)
    cropped_map = scaled_map.subsurface(crop_parameters["crop_rect"])
    screen.blit(cropped_map, (crop_parameters["draw_position_x"], crop_parameters["draw_position_y"]))
    pg.display.flip()

pg.quit()