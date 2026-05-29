# Viking Explorers

## About
This game was created for a competition in the course AE1205 at TU Delft, with the theme being "Dark Ages". The gameplay consists of navigating a viking ship using only information provided by a sun compass.

To run the program, you first need to install the `pygame-ce`, `numpy` and `matplotlib` packages, and then run `main.py`.

[Link to GitHub repository](https://github.com/Antix7/viking-explorers)

## Technical challenges

### World map
Creating a map of the world in Python without compromising performance proved to be a challenge. My first approach was using a satellite image, but cropping and scaling it with pygame resulted in a lot of lag. Instead, I used a numpy array to store whether a given pixel was land or sea. This way the resulting texture size was much smaller, significantly improving performance. This data was stored in a compressed `.npz` file, which took up less than a megabyte of disk space.

### Position of the sun
Simulating a sundial requires answering the following question: for a given time and location, what is the apparent position of the sun in the sky? In code, this is done by repeated coordinate transformations in numpy. Firstly, we start with a latitude and longitude, which is transformed to a surface normal vector in a frame of reference fixed to Earth. Then a rotation around Earth's axis is applied, equal to the number of sidereal days passed since some fixed date. After that, Earth's axial tilt is applied, and a final transformation into an Earth-Sun fixed frame is performed. This coordinate system has the Sun in the x-direction, and from that the elevation and azimuth of the Sun can be computed.

### User interface
The pygame library only provides functions for drawing simple shapes and text, so creating a full UI required some work. I implemented custom button objects to handle user interactions, and created functions for rendering large bodies of text at once, since pygame doesn't support text wrapping.

## Sources
[Topographic-bathymetric map of the world](https://www.ncei.noaa.gov/products/etopo-global-relief-model)
[Viking ship sprite](https://helianthus-games.itch.io/pixel-art-viking-ship-16-directions)
