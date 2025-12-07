import tifffile
import numpy as np
import os

filename = 'test_white.tif'

try:
    with tifffile.TiffWriter(filename, bigtiff=True) as tif:
        # 2x2 grid of 100x100 tiles
        # Tile 0,0: Red
        # Tile 0,1: Green
        # Tile 1,0: White (our "missing" tile simulation)
        # Tile 1,1: Blue
        
        def generator():
            # 0,0 Red
            yield np.full((100, 100, 3), [255, 0, 0], dtype='uint8')
            # 0,1 Green
            yield np.full((100, 100, 3), [0, 255, 0], dtype='uint8')
            # 1,0 White
            yield np.full((100, 100, 3), 255, dtype='uint8')
            # 1,1 Blue
            yield np.full((100, 100, 3), [0, 0, 255], dtype='uint8')

        tif.write(
            generator(),
            shape=(200, 200, 3),
            dtype='uint8',
            tile=(100, 100),
            compression='zlib'
        )
    print("Test file created: test_white.tif")
    
except Exception as e:
    print(f"Error: {e}")
