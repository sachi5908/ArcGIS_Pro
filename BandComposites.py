import arcpy
import os
import re
import sys

# Set your workspace where the unzipped Landsat TIFs are located
arcpy.env.workspace = r"D:\Geoinformatics\composite band files" 
output_folder = r"D:\Geoinformatics\test\Output"

# Ensure output directory exists
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Define the specific scene prefix
prefix = "LC09_L2SP_145043_20251225_20251227_02_T1"

# 1. AUTOMATICALLY DETECT AVAILABLE BANDS
available_bands = {}
for file in os.listdir(arcpy.env.workspace):
    if file.startswith(prefix) and file.upper().endswith(".TIF"):
        match = re.search(r'_SR_B(\d+)', file, re.IGNORECASE)
        if match:
            band_num = int(match.group(1))
            if 1 <= band_num <= 7:
                available_bands[band_num] = file

if not available_bands:
    print("🚨 No bands found for this prefix. Check your folder path and prefix.")
    sys.exit()

# Sort to ensure consistent order for the master composite
sorted_band_nums = sorted(available_bands.keys())
print(f"Detected bands: {sorted_band_nums}")

# 2. DEFINE DESIRED COMBINATIONS (Strict RGB Order)
combinations = {
    "TCC_432": [4, 3, 2],
    "Veg_FCC_543": [5, 4, 3],
    "VegMoist_654": [6, 5, 4],
    "Geology_764": [7, 6, 4],
    "VegSoil_753": [7, 5, 3],
    "MoistVeg_652": [6, 5, 2],
    "GeoSoil_752": [7, 5, 2],
    "VegMoistContrast_562": [5, 6, 2]
}

print("\n--- Phase 1: Generating specific 3-band TIF files ---")

# 3. GENERATE PHYSICAL 3-BAND FILES AND RENAME BANDS
for name, bands in combinations.items():
    if all(b in available_bands for b in bands):
        
        in_rasters = [os.path.join(arcpy.env.workspace, available_bands[b]) for b in bands]
        in_rasters_str = ";".join(in_rasters)
        out_raster = os.path.join(output_folder, f"{prefix}_{name}.tif")
        
        if not os.path.exists(out_raster):
            print(f"Creating {name}...")
            
            # Run CompositeBands
            arcpy.management.CompositeBands(in_rasters_str, out_raster)
            
            # Rename internal bands to avoid UI confusion and collision bugs
            rast_obj = arcpy.Raster(out_raster)
            for i, b_num in enumerate(bands):
                default_name = f"Band_{i+1}"
                target_name = f"L9_Band_{b_num}" 
                try:
                    rast_obj.renameBand(default_name, target_name)
                except Exception as e:
                    print(f"   ⚠️ Could not rename {default_name} to {target_name}: {e}")
            
            # Calculate statistics for perfect immediate contrast
            arcpy.management.CalculateStatistics(out_raster)
            print(f"✅ Saved: {out_raster}")
            
        else:
            print(f"⚠️ File already exists, skipping: {out_raster}")
    else:
        print(f"❌ Skipped {name}: Missing one or more required bands {bands}")


print("\n--- Phase 2: Generating the Master Dynamic Composite ---")

# 4. GENERATE THE MASTER ALL-BAND COMPOSITE
master_out_raster = os.path.join(output_folder, f"{prefix}_DynamicComposite.tif")

if not os.path.exists(master_out_raster):
    print("Creating Master Dynamic Composite (All available bands)...")
    
    # Construct input string using all detected bands in numerical order
    master_in_rasters = [os.path.join(arcpy.env.workspace, available_bands[b]) for b in sorted_band_nums]
    master_in_rasters_str = ";".join(master_in_rasters)
    
    # Run CompositeBands for the master file
    arcpy.management.CompositeBands(master_in_rasters_str, master_out_raster)
    
    # Rename internal bands for the master file
    master_rast_obj = arcpy.Raster(master_out_raster)
    for i, b_num in enumerate(sorted_band_nums):
        default_name = f"Band_{i+1}"
        target_name = f"L9_Band_{b_num}" 
        try:
            master_rast_obj.renameBand(default_name, target_name)
        except Exception as e:
            print(f"   ⚠️ Could not rename {default_name} to {target_name}: {e}")
            
    # Calculate statistics
    arcpy.management.CalculateStatistics(master_out_raster)
    print(f"✅ Saved Master Composite: {master_out_raster}")
else:
    print(f"⚠️ Master file already exists, skipping: {master_out_raster}")

print("\nWorkflow completely finished! All specific composites and your master file are ready.")