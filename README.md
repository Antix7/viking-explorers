# Viking Explorers

## About
This game was created for a competition in the course AE1205 at TU Delft, with the theme being "Dark Ages". The gameplay consists of navigating a Viking sailboat in changing wind conditions, using only information provided by a sun compass.

To run the program, you first need to install the `pygame-ce`, `numpy` and `matplotlib` packages, and then run `main.py`.

[Link to GitHub repository](https://github.com/Antix7/viking-explorers)

## Technical challenges

### World map
Creating a map of the world in Python without compromising performance proved to be a challenge. My first approach was using a satellite image, but cropping and scaling it with pygame resulted in a lot of lag. Instead, I used a numpy array to store whether a given pixel was land or sea. This way the resulting texture size was much smaller, significantly improving performance. This data is stored in a compressed `.npz` file, which takes up less than a megabyte of disk space.

### Position of the sun
Simulating a sundial requires answering the following question: for a given time and location, what is the apparent position of the sun in the sky? In code, this is done by repeated coordinate transformations in numpy. Firstly, we start with a latitude and longitude, which is transformed to a surface normal vector in a frame of reference fixed to Earth. Then a rotation around Earth's axis is applied, equal to the number of sidereal days passed since some fixed date. After that, Earth's axial tilt is applied, and a final transformation into an Earth-Sun fixed frame is performed. This coordinate system has the Sun in the x-direction, and from that the elevation and azimuth of the Sun can be computed.

### Sailing mechanic
The sailing system consists of two parts, the first being a random wind direction generator. A simple approach would be to offset the wind heading by some random amount each frame, but that would result in very jittery motion. Instead, the program generates a sequence of random directions, and smoothly interpolates between them using a sinusoidal ease in/out function, which results in very believable wind patterns. The second challenge is determining the ship's speed as a function of its angle to the wind. Sailboats sail the fastest when going perpendicular to the wind, and can't go directly upwind. Through trial and error, I found a function that approximates this behaviour: $cos(0.3\theta^2 + 0.5\theta - 1.4) + 0.8$, where $\theta$ is the angle between the wind direction and the ship's heading.

### Performance
I already mentioned performance in the World Map section, but there is much more to it. The most critical area is rendering the sundial image. As it turns out, matplotlib is not made for real-time applications, and each sundial image can take up to 200 ms to render. The culprit for this are the latitude lines, which consist of hundreds or thousands of points. My solution was to pre-render those lines, and only update the position of the shadow each frame. The latitude lines are re-computed once per in-game day to keep the sundial accurate. Another area important to performance is rendering the fog around the ship. This is done by repeatedly drawing ellipses decreasing in size and increasing in transparency, and then blurring the result. Doing so every frame would create a lot of lag, so the fog textures are cached based on their dimensions.

### User interface
The pygame library only provides functions for drawing simple shapes and text, so creating a full UI required some work. I implemented custom button objects to handle user interactions, and created functions for rendering large bodies of text at once, since pygame doesn't support text wrapping.

## Sources
[Topographic-bathymetric map of the world](https://www.ncei.noaa.gov/products/etopo-global-relief-model)  
[Viking ship sprite](https://helianthus-games.itch.io/pixel-art-viking-ship-16-directions)  
[Viking helmet icon](https://www.shutterstock.com/image-vector/this-viking-hat-icon-pixel-art-2686193895)  
