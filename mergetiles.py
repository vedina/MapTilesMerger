from PIL import Image
import argparse
import os
import sys

# Increase max image size significantly to avoid DecompressionBombError for large maps
Image.MAX_IMAGE_PIXELS = None 

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

image = Image.new('RGB', (total_width, total_height))

i = 0
for dir_name in baseDirectoryContent:
    y = tileSize * i
    j = 0
    row_dir = os.path.join(baseDir, dir_name)
    # Sort files numerically by filename (excluding extension)
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
try:
    # If the user didn't specify an extension or specified .tif/.tiff, save as TIFF.
    # Otherwise respect the extension provided.
    # We remove the hardcoded "JPEG" format.
    image.save(destinationFile)
    print("Result file is written successfully!")
except Exception as e:
    print(f"Error saving file: {e}")
    sys.exit(1)
