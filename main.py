from math import *
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import pygame as pg
import pygame.freetype as ft # more sophisticated text rendering library
from ui_library import *

# Constants
EARTH_RADIUS = 6371 #[km]
MAP_SCALE = 60*(180/pi) #[px/rad]
MAP_LAT_START = -pi/2
MAP_LON_START = -pi
SUNDIAL_SIMULATION_INTERVAL = timedelta(minutes=20)

# Helper functions to convert between degrees and radians
def to_radians(degrees):
    return degrees*(pi/180)
def to_degrees(radians):
    return radians*(180/pi)

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

# Calculates the apparent position of the sun in the sky for a given location and time
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
    earth_axial_tilt = to_radians(23.44)
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
    # This function runs through time and starts recording the position of the Sun after it rises
    # above a minimum elevation, and stops after it goes back below it.
    start_date -= timedelta(days=1)
    time_step = SUNDIAL_SIMULATION_INTERVAL
    result = {}
    for latitude in latitudes:

        azimuths = []
        elevations = []
        time_offset = timedelta(0)
        previous_elevation = 4 # something larger than pi
        previous_azimuth = 0
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
                azimuths.append(previous_azimuth)
                elevations.append(previous_elevation)
            if record:
                azimuths.append(azimuth)
                elevations.append(elevation)
            if previous_elevation > elevation_bound >= elevation and record:
                record = False
                run = False
            time_offset += time_step
            previous_elevation = elevation
            previous_azimuth = azimuth

        if success:
            result[latitude] = (np.array(azimuths), np.array(elevations))
        else:
            result[latitude] = (np.array([]), np.array([]))

    return result

# Creates a visualization of the sundial using matplotlib and saves it to a file
def create_sundial_plot(latitude, longitude, start_lat, stop_lat, interval, date, min_elevation, sundial_height=1):
    latitudes = np.arange(start_lat, stop_lat, interval)
    sun_path_data = get_sun_path_data(latitudes, date, min_elevation)

    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_yticklabels([])
    ax.set_title("Sundial")
    plot_max_radius = sundial_height/tan(min_elevation)
    ax.set_rlim(0, plot_max_radius)

    for key, [azimuths, elevations] in sun_path_data.items():

        shadow_lengths = sundial_height/np.tan(elevations)
        ax.plot(azimuths+pi, shadow_lengths, label=str(round(np.degrees(key), 2))+'\u00B0')

    elevation, azimuth = get_sun_position(latitude, longitude, date)
    shadow_length = sundial_height/tan(elevation) if elevation > min_elevation else 0
    ax.plot([azimuth+pi, azimuth+pi], [0, shadow_length], color="grey", linewidth=2, label="Shadow")
    ax.set_rmin(0)
    ax.legend()
    plt.savefig('data/sundial.png', bbox_inches='tight', dpi=200)
    plt.close(fig)

# Calculates the position of a point on a sphere in the equirectangular projection
def project_spherical(latitude, longitude):
    x = MAP_SCALE * (longitude-MAP_LON_START)
    y = MAP_SCALE * (latitude-MAP_LAT_START)
    return x, y

# Checks if the map would cover the entire screen after a zoom-out
def is_zoom_out_allowed(zoom_level):
    scaled_map_width = MAP_WIDTH * zoom_level / zoom_factor
    scaled_map_height = MAP_HEIGHT * zoom_level / zoom_factor
    return scaled_map_width >= SCREEN_WIDTH and scaled_map_height >= SCREEN_HEIGHT

# Callback functions for buttons
def quit_game():
    global run
    run = False
def start_game():
    global main_screen_shown
    main_screen_shown = False
def show_sundial(update=False):
    global sundial_shown, sundial_image
    if not update:
        sundial_shown = not sundial_shown
    if not sundial_shown:
        return
    latitude_rounded = to_radians(round(to_degrees(ship_latitude), -1)) # Rounding to the nearest 10 degrees
    create_sundial_plot(ship_latitude, ship_longitude, latitude_rounded - sundial_range, latitude_rounded + sundial_range,
                        sundial_interval, date, to_radians(20))
    sundial_image = pg.image.load("data/sundial.png")

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

# Helper functions for loading files
def load_map():
    # The world map is compressed into a numpy array, where 0 represents sea and 1 land.
    land_sea_mask = np.load("data/land_sea_mask.npz")["mask"]
    MAP_HEIGHT, MAP_WIDTH = land_sea_mask.shape
    rgb_map = np.zeros((MAP_HEIGHT, MAP_WIDTH, 3), dtype=np.uint8)
    rgb_map[land_sea_mask == 0] = SEA_COLOR
    rgb_map[land_sea_mask == 1] = LAND_COLOR
    rgb_map = np.transpose(rgb_map, (1, 0, 2))
    map_surface = pg.surfarray.make_surface(rgb_map)
    return land_sea_mask, map_surface, MAP_WIDTH, MAP_HEIGHT
def load_main_screen_text():
    with open("data/main_screen_text.txt", encoding="utf-8") as file:
        return file.read().strip('\n')

# Checks whether a given position is a land tile
def is_on_land(position_tuple):
    x, y = position_tuple
    x = int(round(x, 0))
    y = MAP_HEIGHT - int(round(y, 0))
    if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
        return raw_map[y][x]
    return 1

# Renders a block of text wrapped to a specific width
def render_wrapped_text(text, font, color, max_width, line_spacing):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        _, test_rect = font.render(test_line, color)
        test_width = test_rect.width
        if test_width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    rendered_lines = [font.render(line, color)[0] for line in lines]
    line_height = rendered_lines[0].get_rect().height + line_spacing
    total_height = line_height * len(rendered_lines)
    total_width = max(surf.get_width() for surf in rendered_lines)
    result = pg.Surface((total_width, total_height), pg.SRCALPHA)
    for i, line_surf in enumerate(rendered_lines):
        result.blit(line_surf, (0, i * line_height))
    return result

# Renders multiple paragraphs of text at once
def render_paragraphs(text, font, color, max_width, line_spacing, par_spacing):
    paragraphs = text.split("\n")
    rendered_paragraphs = []
    for paragraph in paragraphs:
        rendered_paragraphs.append(render_wrapped_text(paragraph, font, color, max_width, line_spacing))
    total_height = sum(p.get_height() for p in rendered_paragraphs) + par_spacing*(len(paragraphs)-1)
    total_width = max(p.get_width() for p in rendered_paragraphs)
    result = pg.Surface((total_width, total_height), pg.SRCALPHA)
    current_y = 0
    for surface in rendered_paragraphs:
        result.blit(surface, (0, current_y))
        current_y += surface.get_height() + par_spacing
    return result

# Common color definitions
SEA_COLOR = hex_to_rgb("#F1C888")
LAND_COLOR = hex_to_rgb("#905918")
FOG_COLOR = hex_to_rgb("#333333")
BUTTON_BASE_COLOR = pg.Color("#bbbbbb")
BUTTON_HOVER_COLOR = pg.Color("#777777")

# Setting up pygame
pg.init()
screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
SCREEN_WIDTH = screen.get_width()
SCREEN_HEIGHT = screen.get_height()
pg.display.set_caption("Viking Explorers")
clock = pg.time.Clock()
font_small = ft.SysFont("segoeuisymbol", 12)
font = ft.SysFont("segoeuisymbol", 20)
font_big = ft.SysFont("segoeuisymbol", 40)

# Showing a loading screen
loading_text, loading_text_rect = font_big.render("Loading...", "white")
screen.fill(FOG_COLOR)
loading_text_rect.center=(SCREEN_WIDTH/2, SCREEN_HEIGHT*0.45)
screen.blit(loading_text, loading_text_rect)
pg.display.flip()

# Setting up pygame (continued)
raw_map, map_surface, MAP_WIDTH, MAP_HEIGHT = load_map()

quit_button = Button(screen, 10, 10, 100, 30, BUTTON_BASE_COLOR, BUTTON_HOVER_COLOR, "red", "Exit", font, quit_game)
sundial_button = Button(screen, 120, 10, 100, 30, BUTTON_BASE_COLOR, BUTTON_HOVER_COLOR, "black", "Sundial", font, show_sundial)
buttons = [quit_button, sundial_button]
num_timewarp_buttons = 3
timewarp_controls = TimewarpControls(screen, 10, 60, 80, 30, 10, BUTTON_BASE_COLOR, BUTTON_HOVER_COLOR, font, num_timewarp_buttons)

# Game state definitions
FPS = 60
MAX_ZOOM = 6.0
MIN_ZOOM = 0.5
zoom_level = 4.0
zoom_factor = 1.2
camera_x = 10950
camera_y = 1750
lmb_held_down = False
ship_latitude = to_radians(59)
ship_longitude = to_radians(5)
ship_velocity = 5 #[m/s]
ship_angular_velocity = ship_velocity/(EARTH_RADIUS*1000) #[rad/s]
sailing = False
ship_turning_velocity = 2 #[rad/s]
ship_heading = 0
horizon_distance = 80 #[km]
date = datetime(900, 5, 1, 18, 0, 0)
sundial_shown = False
sundial_range = to_radians(10) #[rad] 10 degrees up and down
sundial_interval = to_radians(4) #[rad]
sundial_image = pg.Surface((0, 0))
timewarp_factor = 0
timewarp_multiplier = 15
timewarp = 1
main_screen_shown = True
time_since_sundial_refresh = timedelta()
sundial_refresh_interval = timedelta(seconds=1)

# Setting up the main screen
main_screen = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
main_screen.fill(FOG_COLOR)
main_screen_text = load_main_screen_text()
ms_text_rendered = render_paragraphs(main_screen_text, font, "white", SCREEN_WIDTH * 0.8, 2, 10)
ms_text_rect = ms_text_rendered.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.45))
main_screen.blit(ms_text_rendered, ms_text_rect)
continue_button_pos = (ms_text_rect.right-150, ms_text_rect.bottom+10)
continue_button = Button(screen, *continue_button_pos, 150, 40, BUTTON_BASE_COLOR, BUTTON_HOVER_COLOR, "black", "Start game!", font, start_game)

while main_screen_shown:
    clock.tick(FPS)
    mouse_pos = pg.mouse.get_pos()
    for event in pg.event.get():
        continue_button.handle_event(event, mouse_pos)
    continue_button.update(mouse_pos)
    screen.blit(main_screen, (0, 0))
    continue_button.draw()
    pg.display.flip()

# Main game loop
run = True
while run:

    delta_time = clock.tick(FPS) / 1000
    time_since_sundial_refresh += timedelta(seconds=delta_time)
    date += timedelta(seconds=delta_time*timewarp)
    timewarp = timewarp_multiplier**(timewarp_factor+1) # Lowest timewarp is faster than real-time
    mouse_pos = pg.mouse.get_pos()

    # Looping over all events and handling them
    for event in pg.event.get():

        if event.type == pg.QUIT:
            run = False

        # Handling button presses
        for button in buttons:
            button.handle_event(event, mouse_pos)
        timewarp_return = timewarp_controls.handle_event(event, mouse_pos)
        if timewarp_return is not None:
            timewarp_factor = timewarp_return

        # Zooming of the map
        if event.type == pg.MOUSEWHEEL:
            zoom_exponent = 0
            if event.y > 0:
                zoom_exponent = 1
            elif event.y < 0:
                zoom_exponent = -1
            if MAX_ZOOM < zoom_level*(zoom_factor**zoom_exponent) or zoom_level*(zoom_factor**zoom_exponent) < MIN_ZOOM:
                zoom_exponent = 0
            old_zoom = zoom_level
            zoom_level *= zoom_factor**zoom_exponent
            mouse_x, mouse_y = pg.mouse.get_pos()
            camera_x += mouse_x  * (1/old_zoom - 1/zoom_level)
            camera_y += mouse_y * (1/old_zoom - 1/zoom_level)

        if event.type == pg.KEYDOWN:
            # Starting and stopping the ship
            if event.key == pg.K_SPACE:
                sailing = not sailing
            # Timewarp controls
            if event.key == pg.K_LEFT:
                timewarp_factor = max(0, timewarp_factor-1)
            if event.key == pg.K_RIGHT:
                timewarp_factor = min(timewarp_factor+1, num_timewarp_buttons-1)

    # Handling button hover
    for button in buttons:
        button.update(mouse_pos)
    timewarp_controls.update(timewarp_factor=timewarp_factor)

    # Panning of the map
    if pg.mouse.get_pressed()[0]:
        if lmb_held_down:
            mouse_dx, mouse_dy = pg.mouse.get_rel()
            camera_x -= mouse_dx / zoom_level
            camera_y -= mouse_dy / zoom_level
        else:
            lmb_held_down = True
            pg.mouse.get_rel()
    else:
        lmb_held_down = False

    # Ship movement
    pressed_keys = pg.key.get_pressed()
    if pressed_keys[pg.K_a]:
        ship_heading -= ship_turning_velocity * delta_time
    if pressed_keys[pg.K_d]:
        ship_heading += ship_turning_velocity * delta_time

    new_latitude = ship_latitude + ship_angular_velocity * cos(ship_heading) * delta_time * timewarp
    new_longitude = ship_longitude + ship_angular_velocity * sin(ship_heading) * delta_time * timewarp / cos(ship_latitude)

    if not is_on_land(project_spherical(new_latitude, new_longitude)) and sailing:
        ship_latitude = new_latitude
        ship_longitude = new_longitude

    # Checking if the map fills the entire screen and pans it if it doesn't
    camera_x = min(max(camera_x, 0), MAP_WIDTH - SCREEN_WIDTH / zoom_level)
    camera_y = min(max(camera_y, 0), MAP_HEIGHT - SCREEN_HEIGHT / zoom_level)

    # Drawing the map onto the screen
    crop_rect_x = camera_x
    crop_rect_y = camera_y
    crop_rect_width = SCREEN_WIDTH / zoom_level
    crop_rect_height = SCREEN_HEIGHT / zoom_level
    crop_rect = pg.Rect(crop_rect_x, crop_rect_y, crop_rect_width, crop_rect_height)
    visible_subsurface = map_surface.subsurface(crop_rect)
    scaled_surface = pg.transform.scale(visible_subsurface, (
        crop_rect_width*zoom_level,
        crop_rect_height*zoom_level
    ))
    screen.fill((0, 0, 0))
    screen.blit(scaled_surface, (0, 0))

    # Drawing the ship's position as an arrow
    ship_position_x, ship_position_y = project_spherical(ship_latitude, ship_longitude)
    ship_position_y = MAP_HEIGHT - ship_position_y
    ship_position_x_screen = (ship_position_x - camera_x) * zoom_level
    ship_position_y_screen = (ship_position_y - camera_y) * zoom_level
    w, h, p = 9, 11, 10 # width, height, padding of the triangle representing the ship
    tmp_surf = pg.Surface((w+2*p, h+2*p), pg.SRCALPHA)
    pg.draw.polygon(tmp_surf, "red", [[p+w//2, p], [p, p+h-1], [p+w-1, p+h-1]])
    tmp_surf = pg.transform.rotozoom(tmp_surf, to_degrees(-ship_heading), 1)
    render_rect = tmp_surf.get_rect(center=(ship_position_x_screen, ship_position_y_screen))
    screen.blit(tmp_surf, render_rect)

    # Drawing a dark overlay around the ship
    visibility_radius_v = (horizon_distance/EARTH_RADIUS)*MAP_SCALE*zoom_level
    visibility_radius_h = visibility_radius_v/cos(ship_latitude)
    ellipse_rect = pg.Rect(0, 0, visibility_radius_h, visibility_radius_v)
    ellipse_rect.center = (ship_position_x_screen, ship_position_y_screen)
    overlay = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.fill(FOG_COLOR)
    pg.draw.ellipse(overlay, "white", ellipse_rect)
    overlay.set_colorkey("white")
    screen.blit(overlay, (0, 0))

    # Drawing the sundial if it's shown
    if time_since_sundial_refresh >= sundial_refresh_interval:
        time_since_sundial_refresh = timedelta(0)
        if sundial_shown:
            show_sundial(update=True)
    if sundial_shown and sundial_image is not None:
        sundial_ar = sundial_image.width/sundial_image.height
        scaled_sundial_width = SCREEN_HEIGHT*sundial_ar
        sundial_image_scaled = pg.transform.smoothscale(sundial_image, (scaled_sundial_width, SCREEN_HEIGHT))
        screen.blit(sundial_image_scaled, (SCREEN_WIDTH-scaled_sundial_width, 0))
        disclaimer_text = "For readability, the shadow is shown only for sun elevations greater than 20\u00B0"
        disclaimer_text_rendered, disclaimer_text_rect = font_small.render(disclaimer_text, "black")
        disclaimer_text_rect.bottomright = (SCREEN_WIDTH-10, SCREEN_HEIGHT-10)
        screen.blit(disclaimer_text_rendered, disclaimer_text_rect)

    # Drawing the buttons and on-screen variables
    for button in buttons:
        button.draw()
    timewarp_controls.draw()
    sun_elevation, _ = get_sun_position(ship_latitude, ship_longitude, date)
    sun_elevation = round(to_degrees(sun_elevation), 1)
    sun_elevation_text, _ = font_small.render(f"Sun elevation: {sun_elevation}\u00B0", "white")
    screen.blit(sun_elevation_text, (15, 100))
    anchor_text, _ = font_small.render("Anchor: "+("up" if sailing else "down"), "white")
    screen.blit(anchor_text, (15, 115))

    pg.display.flip()

pg.quit()
