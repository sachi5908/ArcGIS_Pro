# Python Scripts for ArcGIS Pro

A collection of Python scripts built with **ArcPy** for Landsat satellite-image processing, spectral-index calculation, band-composite generation, and DEM-based watershed analysis in ArcGIS Pro.

The project includes a browser-based HTML viewer (`python_codes.html`) that presents the scripts with configuration guidance, code-copy controls, and detailed explanations.

## Contents

| Script | Purpose | Main outputs |
|---|---|---|
| `NDVI.py` | Mosaics Landsat 9 Band 4 (Red) and Band 5 (NIR), calculates NDVI, and attempts to clip the result to an Area of Interest (AOI). | `Simple_B4.tif`, `Simple_B5.tif`, `Simple_NDVI_Final.tif` or fallback `Simple_NDVI_Unclipped.tif` |
| `NDWI.py` | Mosaics Landsat Bands 3 and 5, applies the scaling factors in the script, calculates NDWI, creates a threshold-based water mask, and attempts AOI clipping. | `NDWI_Final.tif`, `Water_NDWI.tif`, `Water_NDWI_StudyArea.tif` |
| `BandComposites.py` | Detects available Landsat surface-reflectance bands and creates several three-band composites plus a master composite. | Composite GeoTIFFs and a dynamic all-available-band composite |
| `Watershed.py` | Runs a DEM-based hydrological workflow, including sink filling, flow direction and accumulation, stream extraction, stream ordering, watershed delineation, and sub-basin generation. | Stream network, watershed and sub-basin datasets, logs, status/manifests, and `Watershed_Results.lyrx` |

> **Important:** The HTML viewer contains code snippets for these workflows. Before running them, review the script carefully and configure all input paths, filenames, coordinate systems, and output locations for your own data.

## Features

- Landsat band mosaicking using ArcPy.
- Normalized Difference Vegetation Index (NDVI) calculation.
- Normalized Difference Water Index (NDWI) calculation and threshold-based water-mask creation.
- Automated detection of Landsat surface-reflectance bands.
- Generation of multiple RGB band composites for vegetation, moisture, geology, and soil interpretation.
- DEM preprocessing and hydrological analysis.
- AOI conversion and masking workflows using KML and shapefile data.
- Output handling, processing logs, and ArcGIS Pro layer-file preparation.
- HTML-based script viewer with setup notes, copy-code buttons, and expandable explanations.

## Requirements

- **ArcGIS Pro** with a compatible ArcPy Python environment.
- **Spatial Analyst** extension for the raster-analysis workflows, including NDVI, NDWI, and watershed processing.
- A suitable ArcGIS Pro license. The watershed workflow also checks for a Standard or Advanced-level license for its line-smoothing operation.
- Landsat GeoTIFF band files matching the naming patterns used in the scripts.
- A valid study-area boundary where AOI clipping is required.
- A DEM with a defined coordinate system for watershed analysis.
- Sufficient disk space for intermediate rasters and final outputs.

The scripts use ArcPy, which is supplied with ArcGIS Pro. They are **not intended to run in an ordinary Python installation without ArcGIS Pro and the required licensing**.

## Repository structure

A suggested repository layout is:

```text
arcgis-remote-sensing-scripts/
├── README.md
├── python_codes.html
├── NDVI.py
├── NDWI.py
├── BandComposites.py
└── Watershed.py
```

The HTML file is the viewer supplied with this project. The individual `.py` files above are a suggested organization for saving the code from the viewer; create them if they are not already present in your repository.

## Setup

### 1. Prepare the data

Create separate folders for your input data and outputs. Keep the relevant Landsat bands together for each workflow and avoid mixing unrelated TIFF files into folders that are searched using wildcards.

Example:

```text
D:/Geoinformatics/
├── BAND Files/
│   ├── LC..._B3.TIF
│   ├── LC..._B4.TIF
│   ├── LC..._B5.TIF
│   └── SagarAOI.kml
├── composite band files/
└── test/
    └── Output/
```

These are illustrative paths. Use your own directories and actual filenames.

### 2. Configure the paths

Before execution, check the following settings in the relevant script:

- **NDVI and NDWI:** update `base_dir` and the AOI KML filename. If KML conversion fails, verify the fallback polygon shapefile path as well.
- **Band composites:** update `arcpy.env.workspace`, `output_folder`, and `prefix` so the script can find the correct Landsat scene.
- **Watershed:** update `input_dem` and `output_root`; verify the `propy.bat` path for your ArcGIS Pro installation.

Make sure all input files exist and that the account running ArcGIS Pro has permission to read and write to the selected directories.

### 3. Open the HTML viewer

Open `python_codes.html` in a modern web browser. Select a script tab, read its configuration guide, inspect the code, and use the copy button if needed.

The HTML viewer displays and explains the scripts; it does not replace the ArcGIS Pro environment needed to execute ArcPy code.

## Running the scripts

### NDVI workflow

1. Place the relevant Landsat Band 4 and Band 5 files in the configured workspace.
2. Place the AOI KML in the expected location and verify its filename.
3. Open ArcGIS Pro and use its Python environment.
4. Run the NDVI script.
5. Inspect the generated NDVI raster and verify whether AOI clipping succeeded.

The script uses:

\[
NDVI = \frac{NIR - Red}{NIR + Red}
\]

For the Landsat band mapping in this project, Band 5 is NIR and Band 4 is Red.

### NDWI workflow

1. Place the required Landsat Band 3 and Band 5 files in the configured workspace.
2. Verify the input paths and AOI geometry.
3. Run the NDWI script in the ArcGIS Pro Python environment.
4. Review `NDWI_Final.tif` and the threshold-based water mask.
5. Confirm that the clipped study-area output was produced successfully.

The script uses:

\[
NDWI = \frac{Green - NIR}{Green + NIR}
\]

For the band mapping in this script, Band 3 represents Green and Band 5 represents NIR. The script applies scaling factors before index calculation and sets pixels with non-positive scaled values to NoData.

**Interpretation note:** An NDWI threshold greater than zero is a simple water-screening rule, not a guarantee that every selected pixel is water. Validate the output against imagery, terrain, and known surface conditions.

### Band-composite workflow

1. Put the required Landsat surface-reflectance band files in the configured workspace.
2. Set the scene `prefix` to match your filenames.
3. Set the output directory.
4. Run the script.
5. Inspect the generated composites in ArcGIS Pro and confirm the RGB band order.

The script defines these combinations:

| Composite name | Band order (RGB) | Intended visual use |
|---|---:|---|
| `TCC_432` | 4-3-2 | True-colour-style composite |
| `Veg_FCC_543` | 5-4-3 | Vegetation-oriented false-colour composite |
| `VegMoist_654` | 6-5-4 | Vegetation/moisture contrast |
| `Geology_764` | 7-6-4 | Geological and surface-feature interpretation |
| `VegSoil_753` | 7-5-3 | Vegetation and soil contrast |
| `MoistVeg_652` | 6-5-2 | Moisture and vegetation contrast |
| `GeoSoil_752` | 7-5-2 | Geological and soil contrast |
| `VegMoistContrast_562` | 5-6-2 | Vegetation/moisture contrast |

The script also creates a master composite from the available bands. Actual appearance depends on the data, display stretch, atmospheric conditions, and study area; visual composites alone do not confirm a geological or land-cover interpretation.

### Watershed workflow

1. Open the target **2D map** in ArcGIS Pro and save the project before starting.
2. Configure the input DEM, output folder, threshold, smoothing distance, and ArcGIS Pro Python launcher.
3. Ensure the DEM has a known coordinate system and that the required license and Spatial Analyst extension are available.
4. Paste and run the complete watershed launcher script in the ArcGIS Pro Python window, following the instructions in the HTML viewer.
5. Monitor the progress messages and inspect the generated run folder, log, output datasets, and `Watershed_Results.lyrx`.
6. Review the five prepared layers in the active map and press **Ctrl+S** when you are satisfied with the result.

The supplied workflow projects the DEM to **UTM Zone 44N (EPSG:32644)**. This is appropriate only if that coordinate system suits the study area. Change it when working in a different region. The stream threshold controls the extracted drainage network: a higher threshold generally selects fewer, larger streams, while a lower threshold generally includes more tributaries.

The workflow creates a separate timestamped run directory. The project is not automatically saved, so save it manually after checking the added layers.

## Output and validation

After processing, verify the following:

- The script found all required input bands and the expected scene prefix.
- Input rasters have compatible spatial references, cell sizes, extents, and alignment before mosaicking or raster calculations.
- NDVI and NDWI values are plausible and NoData areas are understood.
- AOI clipping used the intended polygon and did not silently fall back to an unclipped raster.
- Composite RGB channel order matches the intended combination.
- Watershed outputs are non-empty and drainage paths follow the DEM-derived terrain.
- Output layer files have valid data sources and the ArcGIS Pro project is saved when appropriate.

Processing success messages do not replace visual and data-quality checks.

## Troubleshooting

| Problem | What to check |
|---|---|
| No Landsat bands detected | Confirm the folder path, file extensions, filename wildcard, and scene prefix. |
| Spatial Analyst error | Check that the extension is installed, licensed, and available. |
| AOI conversion or clipping fails | Check the KML filename and geometry. Confirm that a valid fallback polygon exists if the script uses one. |
| Empty or incomplete mosaic | Confirm that input lists are not empty and that rasters are compatible. |
| Missing composite output | Verify that all required bands for that combination are present and that the output folder is writable. |
| Watershed worker fails | Read `run.log` and `status.json`; check the DEM path, spatial reference, threshold, license, and `propy.bat` location. |
| Layers are not added to the map | Inspect `Watershed_Results.lyrx` and use **Add Data** to load it manually if necessary. |
| Output already exists | Review overwrite settings and existing files before rerunning the workflow. |

## Limitations and considerations

- These scripts are configured examples, not a universal turnkey pipeline; input paths and settings must be adapted.
- Landsat products must be used with the correct band mapping and scaling appropriate to the product. Check the source product metadata before interpreting results.
- NDWI thresholding is a preliminary classification and may confuse water with shadows or other dark surfaces.
- AOI clipping depends on valid geometry and compatible spatial references.
- The watershed script's UTM zone and flow-processing settings must be appropriate for the study region and DEM.
- Large rasters can require substantial processing time, temporary storage, and memory.
- Inspect outputs before using them in reports, mapping, or scientific conclusions.

## Author

**Sachida Nanda Mahanta**

## License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for the complete license terms.

Copyright (c) 2026 Sachida Nanda Mahanta

Contributions, bug reports, and improvements can be made through the repository's issue tracker or pull requests once this project is published on GitHub.

When reporting an issue, include the ArcGIS Pro version, relevant input-data details, the exact error message, and the affected workflow. Do not upload sensitive or restricted geospatial data.
