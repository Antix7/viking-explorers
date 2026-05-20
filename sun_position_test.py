from math import *
import numpy as np
from datetime import *
import matplotlib.pyplot as plt


# Gives the transformation matrix of a rotation about the Earth's rotation axis, West to East
def get_earth_rotation_matrix(earth_rotation_angle):
    return np.array([
        [cos(earth_rotation_angle), sin(earth_rotation_angle), 0],
        [-sin(earth_rotation_angle), cos(earth_rotation_angle), 0],
        [0, 0, 1]
    ]).T

# Rotates a vector by 90 degrees downwards in the plane containing the vector and the z-axis
def rotate_down(vector):
    r = sqrt(vector[0]**2 + vector[1]**2)
    if r == 0: # Vector pointing straight up
        return np.array([1, 0, 0])
    return np.array([vector[0]*vector[2]/r, vector[1]*vector[2]/r, -r])

# Gives the vector projection of a onto b
def project_vector(a, b):
    return (np.dot(a, b) / np.dot(b, b)) * b

def angle_between_vectors(a, b):
    return acos(np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b)))

# This function calculates the apparent position of the sun in the sky for a given location and time
def get_sun_position(latitude, longitude, date):

    # Calculating the rotation of the Earth with respect to the summer solstice in 1 AD
    summer_solstice_date = datetime(1, 6, 22, 20, 54)
    year_length = timedelta(days=365.256363)
    sidereal_day_length = timedelta(hours=23, minutes=56, seconds=4.100)

    time_since_solstice = date - summer_solstice_date
    years_since_solstice = time_since_solstice/year_length
    earth_orbit_angular_position = years_since_solstice * 2*pi
    days_since_solstice = time_since_solstice/sidereal_day_length
    zero_meridian_position = (8 + 54/60) * (2*pi/24)
    earth_rotation_angular_position = zero_meridian_position + days_since_solstice * 2*pi

    # Performing coordinate transformations to find the direction of the
    # surface normal vector in the Sun-Earth fixed reference frame (sun is always in the x-direction)
    earth_axial_tilt = 23.44 * (pi/180)
    axial_tilt_matrix = np.array([
        [cos(earth_axial_tilt), 0, -sin(earth_axial_tilt)],
        [0, 1, 0],
        [sin(earth_axial_tilt), 0, cos(earth_axial_tilt)]
    ]).T

    earth_centered_fixed = np.array([
        cos(longitude)*cos(latitude),
        sin(longitude)*cos(latitude),
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

create_sundial_plot(np.radians(66), np.radians(5), np.radians(50), np.radians(70), np.radians(2), datetime(1001, 6, 1, hour=16), pi/6, 1)


# plt.savefig('foo.png', bbox_inches='tight')