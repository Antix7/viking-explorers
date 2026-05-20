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

date = datetime(1000, 6, 1, 1)
time_step = timedelta(minutes=5)
x_values = np.arange(0, 501)
lat = 0*(pi/180)
lon = 5*(pi/180)
elevations = []
azimuths = []
for i in x_values:
    elevation, azimuth = get_sun_position(lat, lon, date)
    elevations.append(elevation * (180/pi))
    azimuths.append(azimuth * (180/pi))
    date += time_step


plt.subplot(2,  1, 1)
plt.plot(x_values, np.array(elevations), label="Elevation")
plt.plot(x_values, np.array(azimuths), label="Azimuth")
plt.xlabel('Time [5-minute intervals]')
plt.ylabel('Angle [deg]')
plt.legend()
plt.subplot(2,  1, 2)
plt.plot(np.array(azimuths), np.array(elevations))
plt.xlabel('Sun azimuth [deg]')
plt.ylabel('Sun elevation [deg]')
plt.show()