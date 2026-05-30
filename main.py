from math import *
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use("Agg") # Force headless mode for matplotlib, for sundial rendering performance
import matplotlib.pyplot as plt
import pygame as pg
import pygame.freetype as ft # more sophisticated text rendering library
import ui_library as ui


# Helper functions to convert between degrees and radians
def to_radians(degrees):
    return degrees*(pi/180)
def to_degrees(radians):
    return radians*(180/pi)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

# Constants
EARTH_RADIUS = 6371 #[km]
MAP_SCALE = 60*(180/pi) #[px/rad]
MAP_LAT_START = -pi/2
MAP_LON_START = -pi
SUNDIAL_SIMULATION_INTERVAL = timedelta(minutes=20)
SUNDIAL_MIN_ELEVATION = to_radians(15)

# Common color definitions
SEA_COLOR = hex_to_rgb("#F1C888")
LAND_COLOR = hex_to_rgb("#905918")
FOG_COLOR = hex_to_rgb("#333333")
BUTTON_BASE_COLOR = pg.Color("#bbbbbb")
BUTTON_HOVER_COLOR = pg.Color("#777777")
POPUP_BG_COLOR = pg.Color("#dddddd")
SUNDIAL_BG_COLOR = pg.Color("#fffcf7")

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

# Optimized renderer class, which pre-renders the sun lines and only updates the shadow's position
class SundialRenderer:
    def __init__(self, image_height):
        self.min_elevation = SUNDIAL_MIN_ELEVATION
        self.dpi = 200
        fig_size = image_height/self.dpi
        self.fig, self.ax = plt.subplots(
            subplot_kw={"projection": "polar"},
            dpi=self.dpi,
            figsize=(fig_size, fig_size)
        )
        self.fig.patch.set_alpha(0.0)
        self.fig.set_layout_engine("constrained")
        self.apply_axis_settings()
        self.background_cache = None
        self.shadow_line = None

    def apply_axis_settings(self):
        self.ax.set_theta_zero_location("N")
        self.ax.set_theta_direction(-1)
        self.ax.set_yticklabels([])
        self.ax.set_title("Sundial")
        self.ax.set_rlim(0, 1 / np.tan(self.min_elevation))

    def generate_static_background(self, sun_path_data):
        self.ax.clear()
        self.apply_axis_settings()
        for key, [azimuths, elevations] in sun_path_data.items():
            shadow_lengths = 1/np.tan(elevations)
            self.ax.plot(azimuths+pi, shadow_lengths, label=str(round(np.degrees(key), 2))+'\u00B0', linewidth=1)
        self.shadow_line, = self.ax.plot([], [], color="grey", linewidth=2, label="Shadow")
        self.ax.legend(loc="lower right")
        self.fig.canvas.draw()
        self.background_cache = self.fig.canvas.copy_from_bbox(self.fig.bbox)

    def get_sundial_image(self, elevation, azimuth):
        self.fig.canvas.restore_region(self.background_cache)
        shadow_length = 1 / np.tan(elevation) if elevation > self.min_elevation else 0
        self.shadow_line.set_xdata([azimuth + np.pi, azimuth + np.pi])
        self.shadow_line.set_ydata([0, shadow_length])
        self.ax.draw_artist(self.shadow_line)
        raw_rgba = self.fig.canvas.buffer_rgba()
        size = self.fig.canvas.get_width_height()
        full_plot = pg.image.frombuffer(raw_rgba, size, "RGBA")
        plot_bounding_rect = full_plot.get_bounding_rect() # Crops out the transparent margins
        return full_plot.subsurface(plot_bounding_rect).copy()

# Wrapper function that periodically updates the sun lines and outputs a sundial image
def draw_sundial(latitude, longitude, date):
    global sun_path_data_cache_date
    if date - sun_path_data_cache_date >= timedelta(days=1):
        sun_path_data_cache_date = date
        latitude_rounded = to_radians(round(to_degrees(ship_latitude), -1))  # Rounding to the nearest 10 degrees
        latitudes = np.arange(latitude_rounded - sundial_range, latitude_rounded + sundial_range, sundial_interval)
        sun_path_data = get_sun_path_data(latitudes, date, SUNDIAL_MIN_ELEVATION)
        sundial_renderer.generate_static_background(sun_path_data)
    elevation, azimuth = get_sun_position(latitude, longitude, date)
    return sundial_renderer.get_sundial_image(elevation, azimuth)

# Calculates the position of a point on a sphere in the equirectangular projection
def project_spherical(latitude, longitude):
    longitude = (longitude+pi)%(2*pi) - pi
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
def show_sundial():
    global sundial_shown
    sundial_shown = not sundial_shown
def toggle_fog_popup():
    global is_fog_on
    if is_fog_on:
        toggle_fog_popup.shown = True
    else:
        is_fog_on = True
def disable_fog():
    global is_fog_on
    is_fog_on = False

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
def load_ship_sprites():
    sprites = []
    for i in range(17, 1, -1):
        image = pg.image.load(f"data/ship/ship{i}.png").convert_alpha()
        sprites.append(image)
    return sprites
def load_main_screen_text():
    with open("data/main_screen_text.txt", encoding="utf-8") as file:
        return file.read().strip('\n')

# Checks whether a given position is a land tile
def is_on_land(position_tuple):
    x, y = position_tuple
    x = int(x)
    y = int(MAP_HEIGHT - y)
    if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
        return raw_map[y][x]
    return 1

# Returns a ship sprite that matches given heading the closest
def get_ship_sprite(heading):
    sprite_id = round((heading*16)/(2*pi))%16
    return ship_sprites[sprite_id]

def round_to_multiple(x, multiple):
    return multiple * round(x/multiple)

# An optimized fog renderer that caches textures for performance
class FogRenderer:
    def __init__(self, color):
        self.color = color
        self.cache = {} # What if the cache gets too big? Problem for future me...
        self.ease = lambda x: 0.5*(sin(pi*(x-0.5))+1) # ease-in ease-out sine

    def draw_fog(self, width, height, fog_start_frac=0.5, steps=50):
        margin = 10
        surface = pg.Surface((width+2*margin, height+2*margin), pg.SRCALPHA)
        pg.draw.ellipse(surface, self.color, pg.Rect((0, 0), (width+2*margin, height+2*margin)))
        for i in range(steps, int(fog_start_frac*steps), -1):
            ellipse_ratio = i/steps
            alpha_ratio = (ellipse_ratio - fog_start_frac)/(1 - fog_start_frac)
            rect = pg.Rect(0, 0, width*ellipse_ratio, height*ellipse_ratio)
            rect.center = (width/2+margin, height/2+margin)
            alpha = int(255*self.ease(alpha_ratio))
            pg.draw.ellipse(surface, (*self.color, alpha), rect)
        surface_blurred = pg.transform.box_blur(surface, margin//2)
        return surface_blurred

    def get_fog(self, width, height):
        caching_threshold = 5 #[px]
        width = round_to_multiple(width, caching_threshold)
        height = round_to_multiple(height, caching_threshold)
        if (width, height) in self.cache.keys():
            return self.cache[(width, height)]
        fog_surface = self.draw_fog(width, height)
        self.cache[(width, height)] = fog_surface
        return fog_surface


# Setting up pygame
pg.init()
pg.display.set_icon(pg.image.load("data/icon.ico"))
pg.display.set_caption("Viking Explorers")
screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
SCREEN_WIDTH = screen.get_width()
SCREEN_HEIGHT = screen.get_height()
clock = pg.time.Clock()
font_small = ft.SysFont("segoeuisymbol", 12)
font = ft.SysFont("segoeuisymbol", 20)
font_big = ft.SysFont("segoeuisymbol", 40)
theme = ui.Theme(SCREEN_WIDTH, SCREEN_HEIGHT, BUTTON_BASE_COLOR, BUTTON_HOVER_COLOR, "black", POPUP_BG_COLOR, font, 2)
sundial_height = SCREEN_HEIGHT*0.9
sundial_renderer = SundialRenderer(sundial_height)
fog_renderer = FogRenderer(FOG_COLOR)

# Showing a loading screen
loading_text, loading_text_rect = font_big.render("Loading...", "white")
screen.fill(FOG_COLOR)
loading_text_rect.center=(SCREEN_WIDTH/2, SCREEN_HEIGHT*0.45)
screen.blit(loading_text, loading_text_rect)
pg.display.flip()

# Setting up pygame (continued)
raw_map, map_surface, MAP_WIDTH, MAP_HEIGHT = load_map()
ship_sprites = load_ship_sprites()

quit_button = ui.Button(screen, pg.Rect(10, 10, 100, 30), "Exit", theme, quit_game)
sundial_button = ui.Button(screen, pg.Rect(120, 10, 100, 30), "Sundial", theme, show_sundial)
toggle_fog_button = ui.Button(screen, pg.Rect(10, SCREEN_HEIGHT-40, 150, 30), "Toggle fog", theme, toggle_fog_popup)
buttons = [quit_button, sundial_button, toggle_fog_button]
num_timewarp_buttons = 3
timewarp_controls = ui.TimewarpControls(screen, 10, 50, 80, 30, 10, theme, num_timewarp_buttons)
toggle_fog_text = "Are you sure you want to disable fog? Doing so will make the game incredibly easy. Use this option only if you got completely lost."
toggle_fog_popup = ui.Popup(screen, toggle_fog_text, 500, theme, disable_fog)

# Game state definitions
FPS = 60
MAX_ZOOM = 8.0
MIN_ZOOM = 0.5
zoom_level = 4.0 # current zoom level
zoom_factor = 1.2 # by how much the zoom level changes with each scroll
camera_x = 10950
camera_y = 1750
lmb_held_down = False
ship_latitude = to_radians(59)
ship_longitude = to_radians(5)
ship_velocity = 8 #[m/s] (very fast ship)
ship_angular_velocity = ship_velocity/(EARTH_RADIUS*1000) #[rad/s]
sailing = True
ship_turning_velocity = 2 #[rad/s]
ship_heading = 0
horizon_distance = 120 #[km] (exaggerated for gameplay purposes)
date = datetime(900, 5, 1, 18, 0, 0)
sundial_shown = False
sundial_range = to_radians(10) #[rad] 10 degrees up and down
sundial_interval = to_radians(4) #[rad] interval between sun lines
sun_path_data_cache_date = datetime(1, 1, 1)
timewarp_factor = 0
timewarp_multiplier = 15 # by how much each level of timewarp speeds up the game
timewarp = 1
main_screen_shown = True
is_fog_on = True


# Setting up the main screen
main_screen = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
main_screen.fill(FOG_COLOR)
main_screen_text = load_main_screen_text()
ms_text_rendered = ui.render_paragraphs(main_screen_text, font, "white", SCREEN_WIDTH * 0.8, 2, 10)
ms_text_rect = ms_text_rendered.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.45))
main_screen.blit(ms_text_rendered, ms_text_rect)
continue_button_pos = (ms_text_rect.right-150, ms_text_rect.bottom+10)
continue_button = ui.Button(screen, pg.Rect(continue_button_pos, (150, 40)), "Start game!", theme, start_game)

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

    # Updating time
    delta_time = clock.tick(FPS) / 1000
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
        toggle_fog_popup.handle_event(event, mouse_pos)

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
    toggle_fog_popup.update(mouse_pos)

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
    # Updating the heading to keep the ship moving along a great circle (using Clairaut's relation)
    if sailing:
        ship_heading += ship_angular_velocity * sin(ship_heading) * tan(ship_latitude) * delta_time * timewarp

    new_latitude = ship_latitude + ship_angular_velocity * cos(ship_heading) * delta_time * timewarp
    new_longitude = ship_longitude + ship_angular_velocity * sin(ship_heading) * delta_time * timewarp / cos(ship_latitude)
    # Longitude first on purpose, because heading is defined CW and atan2 CCW
    apparent_ship_heading = atan2(new_longitude-ship_longitude, new_latitude-ship_latitude)

    if not is_on_land(project_spherical(new_latitude, new_longitude)) and sailing:
        ship_latitude = max(to_radians(-89), min(to_radians(89), new_latitude)) # avoid singularities at the poles
        ship_longitude = new_longitude

    # Checking if the map fills the entire screen and pans it if it doesn't
    camera_x = min(max(camera_x, 0), MAP_WIDTH - SCREEN_WIDTH / zoom_level)
    camera_y = min(max(camera_y, 0), MAP_HEIGHT - SCREEN_HEIGHT / zoom_level)

    # Drawing the map onto the screen
    crop_rect_x = int(camera_x)
    crop_rect_y = int(camera_y)
    crop_rect_width = min(int(SCREEN_WIDTH / zoom_level)+2, MAP_WIDTH - crop_rect_x) # 2px more for sub-pixel shift
    crop_rect_height = min(int(SCREEN_HEIGHT / zoom_level)+2, MAP_HEIGHT - crop_rect_y)
    crop_rect = pg.Rect(crop_rect_x, crop_rect_y, crop_rect_width, crop_rect_height)
    # The subsurface() method doesn't copy the original surface, which is critical for performance
    visible_subsurface = map_surface.subsurface(crop_rect)
    scaled_surface = pg.transform.scale(visible_subsurface, (
        crop_rect_width*zoom_level,
        crop_rect_height*zoom_level
    ))
    # Fractional pixel offset so that the map doesn't jump around
    offset_x = -(camera_x - crop_rect_x) * zoom_level
    offset_y = -(camera_y - crop_rect_y) * zoom_level
    screen.fill((0, 0, 0))
    screen.blit(scaled_surface, (offset_x, offset_y))

    # Drawing the ship's position
    ship_position_x, ship_position_y = project_spherical(ship_latitude, ship_longitude)
    ship_position_y = MAP_HEIGHT - ship_position_y
    ship_position_x_screen = (ship_position_x - camera_x) * zoom_level
    ship_position_y_screen = (ship_position_y - camera_y) * zoom_level
    ship_sprite = get_ship_sprite(apparent_ship_heading)
    ship_sprite_scaled = pg.transform.smoothscale_by(ship_sprite, zoom_level*0.2)
    render_rect = ship_sprite_scaled.get_rect(center=(ship_position_x_screen, ship_position_y_screen))
    screen.blit(ship_sprite_scaled, render_rect)

    # Drawing a dark overlay of fog around the ship
    if is_fog_on:
        visibility_radius_v = (horizon_distance/EARTH_RADIUS)*MAP_SCALE*zoom_level
        visibility_radius_h = visibility_radius_v/cos(ship_latitude)

        smooth_fog_texture = fog_renderer.get_fog(visibility_radius_h, visibility_radius_v)
        smooth_fog_rect = smooth_fog_texture.get_rect(center=(ship_position_x_screen, ship_position_y_screen))
        screen.blit(smooth_fog_texture, smooth_fog_rect)

        ellipse_rect = pg.Rect(0, 0, visibility_radius_h, visibility_radius_v)
        ellipse_rect.center = (ship_position_x_screen, ship_position_y_screen)
        overlay = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(FOG_COLOR)
        pg.draw.ellipse(overlay, "white", ellipse_rect)
        overlay.set_colorkey("white")
        screen.blit(overlay, (0, 0))


    # Drawing the sundial if it's shown
    sun_elevation, _ = get_sun_position(ship_latitude, ship_longitude, date)
    is_night = sun_elevation < SUNDIAL_MIN_ELEVATION
    sun_elevation = round(to_degrees(sun_elevation), 1)

    if sundial_shown:
        sundial_image = draw_sundial(ship_latitude, ship_longitude, date)
        sundial_width, sundial_height = sundial_image.size
        sundial_rect = sundial_image.get_rect()
        sundial_rect.right = SCREEN_WIDTH-20
        sundial_rect.centery = SCREEN_HEIGHT/2
        bg_rect = pg.Rect(sundial_rect.left-20, 0, SCREEN_WIDTH-sundial_rect.left+20, SCREEN_HEIGHT)
        pg.draw.rect(screen, SUNDIAL_BG_COLOR, bg_rect)
        screen.blit(sundial_image, sundial_rect)
        disclaimer_text = "For readability, the shadow is shown only for sun elevations greater than 15\u00B0"
        disclaimer_text_rendered, disclaimer_text_rect = font_small.render(disclaimer_text, "black")
        disclaimer_text_rect.bottomright = (SCREEN_WIDTH-10, SCREEN_HEIGHT-10)
        screen.blit(disclaimer_text_rendered, disclaimer_text_rect)
        time_text, time_text_rect = font.render("Nighttime" if is_night else "Daytime", "black")
        time_text_rect.topright = (bg_rect.right - 10, bg_rect.top + 10)
        screen.blit(time_text, time_text_rect)
        # Darkening the sundial if it's nighttime
        if is_night:
            tmp = pg.Surface((bg_rect.width, bg_rect.height), pg.SRCALPHA)
            pg.draw.rect(tmp, (*FOG_COLOR, 80), [0, 0, bg_rect.width, bg_rect.height])
            screen.blit(tmp, bg_rect)


    # Drawing the buttons and on-screen variables
    for button in buttons:
        button.draw()
    timewarp_controls.draw()

    sun_elevation_text, _ = font_small.render(f"Sun elevation: {sun_elevation}\u00B0", "white")
    screen.blit(sun_elevation_text, (15, 90))
    anchor_text, _ = font_small.render("Anchor: "+("up" if sailing else "down"), "white")
    screen.blit(anchor_text, (15, 105))
    fog_text, _ = font_small.render("Fog: " + ("enabled" if is_fog_on else "disabled"), "white")
    screen.blit(fog_text, (15, 120))

    toggle_fog_popup.draw()

    pg.display.flip()

pg.quit()
