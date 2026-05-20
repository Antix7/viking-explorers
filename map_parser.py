import rasterio
from rasterio.enums import Resampling
import numpy as np
import matplotlib.pyplot as plt

def read_topographic_data(scale_factor):
    with rasterio.open("data/elevation_map.tif") as dataset:
        new_height = int(dataset.height * scale_factor)
        new_width = int(dataset.width * scale_factor)
        topographic_data = dataset.read(
            1,
            out_shape=(new_height, new_width),
            resampling=Resampling.bilinear
        )
    return topographic_data

get_saved_mask = 1
if get_saved_mask:
    land_sea_mask = np.load("data/land_sea_mask_testing.npz")["mask"]
else:
    topographic_data = read_topographic_data(1)
    land_sea_mask = (topographic_data > 0).astype(np.uint8)
    np.savez_compressed("data/land_sea_mask_testing.npz", mask=land_sea_mask)
    print(f"Mask created. New array shape: {land_sea_mask.shape}")
