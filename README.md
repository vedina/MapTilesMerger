# Tiles preparation
You can use [TileDownloader](http://sourceforge.net/projects/tiledownloader/) project for dowloading tiles from any
online map server or custom location. But it is writed in Visual Basic and contains hardcoded file extension for tiles :(

# Features
- **Robust Merging**: Handles missing tiles or rows without misalignment. Gaps are filled with white.
- **Large Map Support**: Uses `tifffile` and `BigTIFF` to merge massive maps efficiently (if `numpy` and `tifffile` are installed).
- **Transparency Fix**: Automatically composites transparent (RGBA) tiles onto a white background to prevent black artifacts.
- **Filtering**:
    - **Uniformity Filter**: Skips tiles that are a single solid color.
    - **Size Filter**: `--min-size` option to skip invalid/small files.

# Usage

## Basic
`python mergetiles.py -i "C:/demo/" -o "C:/demo/result.tif"`

## Advanced Options
`python mergetiles.py -i ./tiles -o result.tif --min-size 2000`

- `-i`: Input directory (containing row/col structure).
- `-o`: Output file (supports .tif, .png, .jpg). Use .tif for large maps.
- `--min-size`: Minimum file size in bytes (default 1083). Files smaller than this are treated as empty (white).

## Requirements
For best performance with large maps, install:
`uv pip install tifffile numpy`