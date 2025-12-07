
import os
import sys
import shutil
import numpy as np
from PIL import Image
import tifffile
import subprocess

TEST_DIR = "verify_dataset"
OUTPUT_FILE = "verify_output.tif"

def create_tile(path, color):
    img = Image.new('RGB', (100, 100), color)
    img.save(path)

def setup_test_data():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    
    # Row 0: Full
    os.makedirs(os.path.join(TEST_DIR, "0"), exist_ok=True)
    create_tile(os.path.join(TEST_DIR, "0", "0.png"), (255, 0, 0))   # Red   @ 0,0
    create_tile(os.path.join(TEST_DIR, "0", "1.png"), (0, 255, 0))   # Green @ 0,1

    # Row 1: Missing start (left)
    os.makedirs(os.path.join(TEST_DIR, "1"), exist_ok=True)
    # Missing 0.png
    create_tile(os.path.join(TEST_DIR, "1", "1.png"), (0, 0, 255))   # Blue  @ 1,1

def verify_output():
    try:
        with tifffile.TiffFile(OUTPUT_FILE) as tif:
            data = tif.asarray()
            print(f"Output Matrix Shape: {data.shape} (Expected (200, 200, 3))")
            
            # Check 0,0 (Red)
            pixel_0_0 = data[0, 0]
            if not np.all(pixel_0_0 == [255, 0, 0]):
                print(f"FAIL: 0,0 is {pixel_0_0}, expected Red [255, 0, 0]")
            else:
                print("PASS: 0,0 is Red")

            # Check 0,1 (Green) (Right side of row 0)
            pixel_0_1 = data[0, 100]
            if not np.all(pixel_0_1 == [0, 255, 0]):
                 print(f"FAIL: 0,1 is {pixel_0_1}, expected Green [0, 255, 0]")
            else:
                print("PASS: 0,1 is Green")

            # Check 1,0 (Missing -> White) (Left side of row 1)
            pixel_1_0 = data[100, 0]
            if not np.all(pixel_1_0 == [255, 255, 255]):
                print(f"FAIL: 1,0 (Missing Left) is {pixel_1_0}, expected White [255, 255, 255]")
            else:
                print("PASS: 1,0 is White (Correctly filled missing tile)")

            # Check 1,1 (Blue) (Right side of row 1)
            # If implementation is wrong (shifting), this might have been at 1,0
            pixel_1_1 = data[100, 100]
            if not np.all(pixel_1_1 == [0, 0, 255]):
                print(f"FAIL: 1,1 is {pixel_1_1}, expected Blue [0, 0, 255]")
            else:
                print("PASS: 1,1 is Blue (Correctly placed)")

    except Exception as e:
        print(f"Verification Failed with error: {e}")

def main():
    print("Setting up test data...")
    setup_test_data()
    
    print("Running mergetiles.py...")
    cmd = [sys.executable, "mergetiles.py", "-i", TEST_DIR, "-o", OUTPUT_FILE]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    if res.returncode != 0:
        print("Mergetiles failed!")
        print(res.stderr)
        return

    print("Verifying pixels...")
    verify_output()
    
    # Cleanup
    # shutil.rmtree(TEST_DIR)

if __name__ == "__main__":
    main()
