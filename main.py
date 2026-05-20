from math import *
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import pygame as pg
from pygame.constants import *
from ui_library import *

MAP_SCALE = 2400*18/pi #[px/rad]
MAP_LAT_START = (pi/2)*(4/9)
MAP_LON_START = -(pi/2)*(7/9)

# Gives the transformation matrix of a rotation about the Earth's rotation axis, West to East
def get_earth_rotation_matrix(earth_rotation_angle):
    return np.array([
        [cos(earth_rotation_angle), sin(earth_rotation_angle), 0],
        [-sin(earth_rotation_angle), cos(earth_rotation_angle), 0],
        [0, 0, 1]
    ]).T

# Rotates a vector by 90 degrees downwards in the plane containing the vector and the z-axis
def rotate_down(vector):
    r = sqrt(vector[0] ** 2 + vector[1] ** 2)
    if r == 0:  # Vector pointing straight up
        return np.array([1, 0, 0])
    return np.array([vector[0] * vector[2] / r, vector[1] * vector[2] / r, -r])

# Gives the vector projection of a onto b
def project_vector(a, b):
    return (np.dot(a, b) / np.dot(b, b)) * b

def angle_between_vectors(a, b):
    return acos(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# This function calculates the apparent position of the sun in the sky for a given location and time
def get_sun_position(latitude, longitude, date):
    # Calculating the rotation of the Earth with respect to the summer solstice in 1 AD
    summer_solstice_date = datetime(1, 6, 22, 20, 54)
    year_length = timedelta(days=365.256363)
    sidereal_day_length = timedelta(hours=23, minutes=56, seconds=4.100)

    time_since_solstice = date - summer_solstice_date
    years_since_solstice = time_since_solstice / year_length
    earth_orbit_angular_position = years_since_solstice * 2 * pi
    days_since_solstice = time_since_solstice / sidereal_day_length
    zero_meridian_position = (8 + 54 / 60) * (2 * pi / 24)
    earth_rotation_angular_position = zero_meridian_position + days_since_solstice * 2 * pi

    # Performing coordinate transformations to find the direction of the
    # surface normal vector in the Sun-Earth fixed reference frame (sun is always in the x-direction)
    earth_axial_tilt = 23.44 * (pi / 180)
    axial_tilt_matrix = np.array([
        [cos(earth_axial_tilt), 0, -sin(earth_axial_tilt)],
        [0, 1, 0],
        [sin(earth_axial_tilt), 0, cos(earth_axial_tilt)]
    ]).T

    earth_centered_fixed = np.array([
        cos(longitude) * cos(latitude),
        sin(longitude) * cos(latitude),
        sin(latitude)
    ])
    days_rotation_matrix = get_earth_rotation_matrix(earth_rotation_angular_position)
    earth_centered_inertial = np.dot(days_rotation_matrix, earth_centered_fixed)
    local_south_direction = rotate_down(earth_centered_inertial)

    year_rotation_matrix = get_earth_rotation_matrix(earth_orbit_angular_position)
    surface_normal = np.dot(year_rotation_matrix, np.dot(axial_tilt_matrix, earth_centered_inertial))
    local_south_direction = np.dot(year_rotation_matrix, np.dot(axial_tilt_matrix, local_south_direction))
    sun_direction = np.array([1, 0, 0])

    # Using the surface normal direction and the sun direction to calculate the elevation angle and azimuth of the Sun
    local_sun_direction = sun_direction - project_vector(sun_direction, surface_normal)

    sun_elevation_angle = angle_between_vectors(local_sun_direction, sun_direction)
    if np.dot(surface_normal, sun_direction) < 0:
        sun_elevation_angle *= -1
    sun_azimuth = angle_between_vectors(local_sun_direction, local_south_direction)
    local_west = np.cross(local_south_direction, surface_normal)
    if np.dot(local_west, local_sun_direction) < 0:
        sun_azimuth = 2*pi - sun_azimuth
    sun_azimuth = (sun_azimuth + pi)%(2*pi)

    return sun_elevation_angle, sun_azimuth

# Returns the path of the Sun form sunrise to sunset for a range of latitudes
def get_sun_path_data(latitudes, start_date, elevation_bound):
    start_date -= timedelta(days=1)
    time_step = timedelta(minutes=5)
    result = {}
    for latitude in latitudes:

        azimuths = []
        elevations = []
        time_offset = timedelta(0)
        previous_elevation = 4 # something larger than pi
        run = True
        record = False
        success = True

        while run:
            if time_offset > timedelta(days=2):
                success = False
                break
            elevation, azimuth = get_sun_position(latitude, 0, start_date+time_offset)
            if previous_elevation < elevation_bound <= elevation:
                record = True
            if record:
                azimuths.append(azimuth)
                elevations.append(elevation)
            if previous_elevation > elevation_bound >= elevation and record:
                record = False
                run = False
            time_offset += time_step
            previous_elevation = elevation

        if success:
            result[latitude] = (np.array(azimuths), np.array(elevations))
        else:
            result[latitude] = (np.array([]), np.array([]))

    return result

# Creates a visualization of the sundial using matplotlib
def create_sundial_plot(latitude, longitude, start_lat, stop_lat, interval, date, min_elevation, sundial_height=1):
    latitudes = np.arange(start_lat, stop_lat, interval)
    sun_path_data = get_sun_path_data(latitudes, date, min_elevation)

    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_yticklabels([])
    ax.set_title("Sundial")

    for key, [azimuths, elevations] in sun_path_data.items():

        shadow_lengths = sundial_height/np.tan(elevations)
        ax.plot(azimuths+pi, shadow_lengths, label=str(round(np.degrees(key), 2)))

    elevation, azimuth = get_sun_position(latitude, longitude, date)
    shadow_length = sundial_height/tan(elevation)
    ax.plot([azimuth+pi, azimuth+pi], [0, shadow_length], color="grey", linewidth=2, label="Shadow")
    ax.set_rmin(0)
    ax.legend()
    fig.show()

# Calculates the position of a point on a sphere in the equirectangular projection
def project_spherical(latitude, longitude):
    x = MAP_SCALE * (longitude-MAP_LON_START)
    y = MAP_SCALE * (latitude-MAP_LAT_START)
    return x, y

# Determines how the map image should be cropped and positioned on the screen
def get_crop_parameters(camera_x, camera_y, scaled_map_width, scaled_map_height):
    top_left_x = max(-camera_x, 0)
    top_left_y = max(-camera_y, 0)
    bottom_right_x = min(window_width-camera_x, scaled_map_width)
    bottom_right_y = min(window_height-camera_y, scaled_map_height)
    crop_rect = pg.Rect(
        top_left_x, top_left_y,
        bottom_right_x - top_left_x,
        bottom_right_y - top_left_y)
    draw_position_x = 0.0 if camera_x <= 0 else camera_x
    draw_position_y = 0.0 if camera_y <= 0 else camera_y
    return crop_rect, draw_position_x, draw_position_y

# Checks if the map would cover the entire screen after a zoom-out
def is_zoom_out_allowed(zoom_level):
    map_width = map_image.get_rect().width * zoom_level / zoom_factor
    map_height = map_image.get_rect().height * zoom_level / zoom_factor
    return map_width >= window_width and map_height >= window_height

# Setting up pygame
pg.init()

screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
window_width = screen.get_width()
window_height = screen.get_height()
pg.display.set_caption("Viking Explorers")
map_image = pg.image.load("data/game_map.jpg").convert_alpha()

font = pg.font.SysFont('Arial', 20, bold=True)
button = Button(10, 10, 100, 30, pg.Color("#999999"), pg.Color("#777777"), "red", "Exit", font)

zoom_level = 0.1
zoom_factor = 1.2
camera_x = 0
camera_y = 0
lmb_held_down = False
ship_latitude = (pi/3)
ship_longitude = 0
ship_velocity = 0.001 #[rad/whatever]

# Main game loop
run = True
while run:
    mouse_pos = pg.mouse.get_pos()
    for event in pg.event.get():
        if event.type == QUIT:
            run = False

        def quit_game():
            global run
            run = False
        button.handle_event(event, mouse_pos, quit_game)

        # Zooming of the map
        if event.type == MOUSEWHEEL:
            zoom_exponent = 0
            if event.y > 0:
                zoom_exponent = 1
            elif event.y < 0:
                if is_zoom_out_allowed(zoom_level):
                    zoom_exponent = -1
            zoom_level *= zoom_factor**zoom_exponent
            mouse_x, mouse_y = pg.mouse.get_pos()
            camera_x = mouse_x + (camera_x - mouse_x) * (zoom_factor**zoom_exponent)
            camera_y = mouse_y + (camera_y - mouse_y) * (zoom_factor**zoom_exponent)

    button.update(mouse_pos)

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

    # Crude ship movement
    pressed_keys = pg.key.get_pressed()
    if pressed_keys[K_w]:
        ship_latitude += ship_velocity
    if pressed_keys[K_s]:
        ship_latitude -= ship_velocity
    if pressed_keys[K_d]:
        ship_longitude += ship_velocity
    if pressed_keys[K_a]:
        ship_longitude -= ship_velocity

    # Checking if the map fills the entire screen and pans it if it doesn't
    map_width = map_image.get_rect().width * zoom_level
    map_height = map_image.get_rect().height * zoom_level
    camera_x = max(min(camera_x, 0), window_width - map_width)
    camera_y = max(min(camera_y, 0), window_height - map_height)

    # Drawing the map on the screen
    screen.fill((0, 0, 0))
    scaled_map = pg.transform.smoothscale_by(map_image, zoom_level)
    crop_parameters = get_crop_parameters(
        camera_x, camera_y,
        scaled_map.get_rect().width, scaled_map.get_rect().height)
    cropped_map = scaled_map.subsurface(crop_parameters[0])
    screen.blit(cropped_map, (crop_parameters[1], crop_parameters[2]))

    # Drawing the ship's position
    ship_position_x, ship_position_y = project_spherical(ship_latitude, ship_longitude)
    ship_position_y = map_image.get_rect().height - ship_position_y
    ship_position_x_scaled = ship_position_x * zoom_level + camera_x
    ship_position_y_scaled = ship_position_y * zoom_level + camera_y
    pg.draw.circle(screen, "red", (ship_position_x_scaled, ship_position_y_scaled), 3)

    button.draw(screen)

    pg.display.flip()

pg.quit()

#F1C888 - ocean
#905918 - land