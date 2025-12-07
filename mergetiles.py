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

# Filter for numeric directories (likely zoom levels or rows) if needed, 
# but original script didn't strictly enforce, just sorted as int.
# Let's keep it robust.
baseDirectoryContent = [d for d in baseDirectoryContent if d.isdigit()]

verticalTilesCount = len(baseDirectoryContent)

if verticalTilesCount == 0:
    print("Error! Base directory is empty or contains no numeric subdirectories.")
    sys.exit(1)

# Sort rows numerically
baseDirectoryContent.sort(key=lambda x: int(x))

firstDirectoryContent = get_immediate_files(os.path.join(baseDir, baseDirectoryContent[0]))
horizontalTilesCount = len(firstDirectoryContent)
if horizontalTilesCount == 0:
    print("Error! First tile directory is empty. Please check tile files.")
    sys.exit(1)

try:
    first_row_dir = os.path.join(baseDir, baseDirectoryContent[0])
    first_files = sorted(get_immediate_files(first_row_dir), key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else 0)
    
    if not first_files:
         print("Error! No files found in the first row directory.")
         sys.exit(1)

    firstTilePath = os.path.join(first_row_dir, first_files[0])
    firstTile = Image.open(firstTilePath)
    tileSize = firstTile.size[0]
    print(f"Detected tile size: {tileSize}x{tileSize}")
except Exception as e:
    print(f"Error! An error occurred while finding first tile: {e}")
    sys.exit(1)

# Calculate total size
total_width = tileSize * horizontalTilesCount
total_height = tileSize * verticalTilesCount
print(f"Merged image size: {total_width}x{total_height}")

# Use tifffile for memory efficient writing if available and output is tiff
use_tifffile = HAS_TIFFFILE and (destinationFile.lower().endswith('.tif') or destinationFile.lower().endswith('.tiff'))

if use_tifffile:
    print("Using memory-efficient TIFF writing with BigTiff and Deflate compression...", flush=True)
    
    def tile_generator(base_dir, dirs, tile_size, h_count, v_count):
        total_tiles = h_count * v_count
        processed = 0
        
        # Iterate row by row (vertical)
        for dir_name in dirs:
            row_dir = os.path.join(base_dir, dir_name)
            
            # Get files for this row, mapped by column index logic
            # The original script sorts files numerically. check filename is column index?
            # Original: key=lambda x: int(x.split('.')[0])
            # We need to be careful to match the strictly expected grid (h_count, v_count).
            # If files are missing in the sequence, we must yield blanks to keep alignment!
            
            # This requires we know the EXACT start/end or we just iterate what we have?
            # The original PIL logic calculates 'x' and 'y' based on *available* files.
            # "x = tileSize * j", "y = tileSize * i"
            # It blindly places the j-th file at the j-th position.
            # If there are gaps in filenames (e.g. 1.png, 3.png), PIL logic would place 3.png at x=tileSize*1 (2nd slot).
            # This implies the original logic assumes contiguous files or just packs them.
            # However, `horizontalTilesCount` is derived from `firstDirectoryContent` length.
            # If rows have different lengths, the PIL logic might produce jagged edges or misalignments if strictly grid-based?
            # The original logic:
            # i = 0 ... i++ (for each dir)
            # j = 0 ... j++ (for each file in dir)
            # So it strictly packs tiles into a grid of size (total_width, total_height).
            # It DOES NOT use the filename as the coordinate, only for sorting!
            # So 1.png, 50.png will be placed at 0,0 and 0,1 respectively.
            # I will replicate this behavior: Yield all files found in sorted order.
            # BUT, TiffWriter with 'tile' argument writes a grid. 
            # We must ensure we yield exactly (rows * cols) tiles.
            # Original logic: "horizontalTilesCount = len(firstDirectoryContent)"
            # "verticalTilesCount = len(baseDirectoryContent)"
            # "image = Image.new(..., (tileSize * horizontalTilesCount, tileSize * verticalTilesCount))"
            # It assumes a rectangular grid where every row has 'horizontalTilesCount' tiles.
            # If a row has FEWER tiles, the original PIL logic works because it just stops pasting for that row (leaving rest black/transparent).
            # TiffWriter expects a full grid if we define shape.
            # We must pad rows to 'horizontalTilesCount' if they are short.
            
            files = sorted(get_immediate_files(row_dir), key=lambda x: int(os.path.splitext(x)[0]) if os.path.splitext(x)[0].isdigit() else 0)
            
            current_row_count = 0
            for file_name in files:
                tilePath = os.path.join(row_dir, file_name)
                try:
                    with Image.open(tilePath) as tile:
                        if tile.mode != 'RGB':
                            tile = tile.convert('RGB')
                        yield np.asarray(tile)
                except Exception as e:
                    print(f"Warning: Failed to process tile {tilePath}: {e}", flush=True)
                    # Yield black tile on error to skip? Or re-raise? 
                    # Original script printed warning and continued (leaving previous content or void).
                    # We yield a white tile.
                    yield np.full((tile_size, tile_size, 3), 255, dtype='uint8')
                
                current_row_count += 1
                processed += 1
                if current_row_count >= h_count:
                    break # Don't yield more than we allocated width for
            
            # Pad row if short
            while current_row_count < h_count:
                yield np.full((tile_size, tile_size, 3), 255, dtype='uint8')
                current_row_count += 1
                processed += 1

            print(f"Processed row {dirs.index(dir_name)+1}/{len(dirs)}", end='\r', flush=True)

    try:
        with tifffile.TiffWriter(destinationFile, bigtiff=True) as tif:
            tif.write(
                tile_generator(baseDir, baseDirectoryContent, tileSize, horizontalTilesCount, verticalTilesCount),
                shape=(total_height, total_width, 3),
                dtype='uint8',
                tile=(tileSize, tileSize),
                compression='zlib'
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
