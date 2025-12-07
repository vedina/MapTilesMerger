from PIL import Image
import argparse
import os
import sys

# Increase max image size significantly to avoid DecompressionBombError for large maps
# Increase max image size significantly to avoid DecompressionBombError for large maps
Image.MAX_IMAGE_PIXELS = None 

try:
    import tifffile
    import numpy as np
    HAS_TIFFFILE = True
except ImportError:
    HAS_TIFFFILE = False
    print("Warning: 'tifffile' or 'numpy' not found. Large TIFF merging will not be memory efficient.")
    print("Install them with: uv pip install tifffile numpy")

def get_immediate_subdirectories(dir):
    try:
        return [name for name in os.listdir(dir)
                if os.path.isdir(os.path.join(dir, name))]
    except OSError as e:
        print(f"Error accessing directory '{dir}': {e}")
        return []


def get_immediate_files(dir):
    try:
        return [name for name in os.listdir(dir)
                if os.path.isfile(os.path.join(dir, name))]
    except OSError as e:
         print(f"Error accessing directory '{dir}': {e}")
         return []


print("Start map tiles merge...")

parser = argparse.ArgumentParser()

parser.add_argument("-i", action="store", dest='baseDir', help="Input directory path")
parser.add_argument("-o", action="store", dest='destinationFile', help="Output file path")
parser.add_argument("--min-size", action="store", dest='minSize', type=int, default=1083, help="Minimum file size in bytes (default 1083)")
args = parser.parse_args()

if not args.baseDir:
    print("Error! Input directory is not specified. Please use -i argument.")
    sys.exit(1)
else:
    baseDir = args.baseDir

if not args.destinationFile:
    print("Error! Output file is not specified. Please use -o argument.")
    sys.exit(1)
else:
    destinationFile = args.destinationFile

try:
    baseDirectoryContent = get_immediate_subdirectories(baseDir)
except Exception as e:
    print(f"Error! Base directory not found: {e}")
    sys.exit(1)

# Scan all directories to establish the global grid (Bounding Box)
print("Scanning directories for grid dimensions...")
row_dirs = {} # map row_index -> dir_name
all_cols = []
all_rows = []

for d in baseDirectoryContent:
    try:
        r_idx = int(d)
        row_dirs[r_idx] = d
        all_rows.append(r_idx)
        
        # Scan files in this row to find columns
        r_path = os.path.join(baseDir, d)
        files = get_immediate_files(r_path)
        for f in files:
            name_no_ext = os.path.splitext(f)[0]
            if name_no_ext.isdigit():
                all_cols.append(int(name_no_ext))
    except ValueError:
        continue

if not all_rows or not all_cols:
    print("Error! Could not find any valid numeric row/column structures.")
    sys.exit(1)

min_row, max_row = min(all_rows), max(all_rows)
min_col, max_col = min(all_cols), max(all_cols)

total_rows_count = max_row - min_row + 1
total_cols_count = max_col - min_col + 1

print(f"Grid detected: Row range [{min_row}, {max_row}], Col range [{min_col}, {max_col}]")
print(f"Grid dimensions: {total_cols_count} cols x {total_rows_count} rows")

# Detect tile size from the first available tile
try:
    first_row_idx = all_rows[0]
    first_row_dir = os.path.join(baseDir, row_dirs[first_row_idx])
    # Find a valid file in this row
    valid_files = [f for f in get_immediate_files(first_row_dir) if os.path.splitext(f)[0].isdigit()]
    if not valid_files:
        raise Exception("First row directory contains no valid images.")
    
    firstTilePath = os.path.join(first_row_dir, valid_files[0])
    with Image.open(firstTilePath) as img:
        tileSize = img.size[0]
    print(f"Detected tile size: {tileSize}x{tileSize}")
except Exception as e:
    print(f"Error checking tile size: {e}")
    sys.exit(1)

# Calculate total pixel size
total_width = tileSize * total_cols_count
total_height = tileSize * total_rows_count
print(f"Merged image size: {total_width}x{total_height}")

# Use tifffile for memory efficient writing if available and output is tiff
use_tifffile = HAS_TIFFFILE and (destinationFile.lower().endswith('.tif') or destinationFile.lower().endswith('.tiff'))

if use_tifffile:
    print("Using memory-efficient TIFF writing with BigTiff and Deflate compression...", flush=True)
    
    def tile_generator(base_dir, row_map, start_r, end_r, start_c, end_c, tile_sz):
        # Iterate over the full bounding box
        for r in range(start_r, end_r + 1):
            
            # Check if row folder exists
            row_exists = r in row_map
            row_path = os.path.join(base_dir, row_map[r]) if row_exists else None
            
            # Optimization: Pre-fetch existing columns for this row if it exists
            existing_cols = set()
            if row_exists:
                try:
                    files = get_immediate_files(row_path)
                    for f in files:
                        name, _ = os.path.splitext(f)
                        if name.isdigit():
                            existing_cols.add(int(name))
                except OSError:
                    pass # Treat as empty row

            for c in range(start_c, end_c + 1):
                # Try to yield the tile
                tile_yielded = False
                
                if row_exists and c in existing_cols:
                    # Construct potential filenames. 
                    # We only know the int index 'c'. The extension might vary? 
                    # The set logic above stripped extension. We need the real filename.
                    # Let's simple check strict png/jpg or just listdir match.
                    # For performance, let's assume .png or .jpg or match what we found.
                    # Re-scanning listdir every time is slow. 
                    # Better: when building `existing_cols`, store map {col_idx: filename}
                    pass 

            # RE-OPTIMIZED LOOP
            # To avoid re-scanning, let's do it cleaner per row.
            pass

    # Redefine generator with better scope
    def robust_tile_generator(base_dir, row_map, start_r, end_r, start_c, end_c, tile_sz, min_size):
        total_tiles = (end_r - start_r + 1) * (end_c - start_c + 1)
        processed = 0
        
        for r in range(start_r, end_r + 1):
            row_map_cols = {} # col_idx -> filename
            if r in row_map:
                try:
                    r_path = os.path.join(base_dir, row_map[r])
                    for f in os.listdir(r_path):
                        name, ext = os.path.splitext(f)
                        if name.isdigit() and os.path.isfile(os.path.join(r_path, f)):
                            row_map_cols[int(name)] = f
                except OSError:
                    pass

            for c in range(start_c, end_c + 1):
                img_data = None
                if c in row_map_cols:
                    f_name = row_map_cols[c]
                    try:
                        p = os.path.join(base_dir, row_map[r], f_name)
                        
                        # Filter by size
                        if os.path.getsize(p) < min_size:
                            # print(f"DEBUG: Skipping small file {f_name} ({os.path.getsize(p)} bytes)", flush=True)
                            img_data = None # Will be treated as white
                        else:
                            with Image.open(p) as tile:
                                if tile.mode in ('RGBA', 'LA') or (tile.mode == 'P' and 'transparency' in tile.info):
                                    # Create a white background image
                                    bg = Image.new('RGB', tile.size, (255, 255, 255))
                                    # Paste the tile on top, using alpha channel as mask if available
                                    if tile.mode in ('RGBA', 'LA'):
                                        bg.paste(tile, mask=tile.split()[-1])
                                    else:
                                        bg.paste(tile.convert('RGBA'), mask=tile.convert('RGBA').split()[-1])
                                    tile = bg
                                elif tile.mode != 'RGB':
                                    tile = tile.convert('RGB')
                                img_data = np.asarray(tile)
                                
                                # Ensure shape is correct (handle potentially corrupt/wrong size tiles?)
                                if img_data.shape != (tile_sz, tile_sz, 3):
                                    pass # Warn?
                                
                                # Filter by Uniformity (Empty/Solid Color)
                                # Check if all pixels are equal to the first pixel
                                if np.all(img_data == img_data[0,0]):
                                    # print(f"DEBUG: Skipping uniform tile {f_name}", flush=True)
                                    img_data = None # Treat as white
                                    
                    except Exception as e:
                        print(f"Error reading {f_name}: {e}")
                
                if img_data is None:
                    # White tile
                    img_data = np.full((tile_sz, tile_sz, 3), 255, dtype='uint8')
                
                yield img_data
                processed += 1
            
            print(f"Processed row {r} ({(processed/(total_tiles+1))*100:.1f}%)", end='\r', flush=True)

    try:
        with tifffile.TiffWriter(destinationFile, bigtiff=True) as tif:
            tif.write(
                robust_tile_generator(baseDir, row_dirs, min_row, max_row, min_col, max_col, tileSize, args.minSize),
                shape=(total_height, total_width, 3),
                dtype='uint8',
                tile=(tileSize, tileSize),
                compression='zlib',
                photometric='rgb'
            )
        print("\nResult file is written successfully via TiffWriter!", flush=True)
    except Exception as e:
        print(f"\nError using TiffWriter: {e}", flush=True)
        sys.exit(1)

else:
    # Legacy PIL in-memory method
    if HAS_TIFFFILE and not (destinationFile.lower().endswith('.tif') or destinationFile.lower().endswith('.tiff')):
        print("Output not TIFF, falling back to PIL in-memory merge (high memory usage).")
    elif not HAS_TIFFFILE:
        print("tifffile not found, falling back to PIL in-memory merge (high memory usage).")

    try:
        image = Image.new('RGB', (total_width, total_height), (255, 255, 255))
        
        i = 0
        for dir_name in baseDirectoryContent:
            y = tileSize * i
            j = 0
            row_dir = os.path.join(baseDir, dir_name)
            files = sorted(get_immediate_files(row_dir), key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else 0)
            
            for file_name in files:
                tilePath = os.path.join(row_dir, file_name)
                try:
                    tile = Image.open(tilePath)
                    x = tileSize * j
                    image.paste(tile, (x, y))
                except Exception as e:
                     print(f"Warning: Failed to process tile {tilePath}: {e}")
                j += 1
            i += 1
        
        print(f"Saving result to {destinationFile}...")
        image.save(destinationFile)
        print("Result file is written successfully!")
    except Exception as e:
        print(f"Error saving file: {e}")
        sys.exit(1)
