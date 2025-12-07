import tifffile
import numpy as np
import os

filename = 'test_white_fixed.tif'

try:
    print("Creating test TIFF...")
    with tifffile.TiffWriter(filename, bigtiff=True) as tif:
        # 2x2 grid of 100x100 tiles
        # Tile 0,0: Red [255, 0, 0]
        # Tile 0,1: Green [0, 255, 0]
        # Tile 1,0: White [255, 255, 255] (Simulated missing)
        # Tile 1,1: Blue [0, 0, 255]
        
        def generator():
            # 0,0 Red
            t = np.zeros((100, 100, 3), dtype='uint8')
            t[:,:] = [255, 0, 0]
            yield t
            # 0,1 Green
            t = np.zeros((100, 100, 3), dtype='uint8')
            t[:,:] = [0, 255, 0]
            yield t
            # 1,0 White
            t = np.full((100, 100, 3), 255, dtype='uint8')
            yield t
            # 1,1 Blue
            t = np.zeros((100, 100, 3), dtype='uint8')
            t[:,:] = [0, 0, 255]
            yield t

        # NOTE: tile argument is strictly (H, W) tuple. 
        # The data yielded must match this tile shape in H,W.
        # shape argument is (TotalH, TotalW, Channels).
        tif.write(
            generator(),
            shape=(200, 200, 3),
            dtype='uint8',
            tile=(100, 100),
            compression='zlib',
            photometric='rgb'
        )
    print(f"Test file created: {filename}")
    
    # Verify content
    print("Verifying pixels...")
    with tifffile.TiffFile(filename) as tif:
        data = tif.asarray()
        
        # Check 1,0 (White) -> pixel at y=100, x=0
        pixel = data[100, 0]
        print(f"Pixel at 100,0 (expected White): {pixel}")
        if np.all(pixel == [255, 255, 255]):
            print("SUCCESS: Pixel is WHITE [255, 255, 255]")
        else:
            print("FAILURE: Pixel is NOT WHITE")

except Exception as e:
    print(f"Error: {e}")
