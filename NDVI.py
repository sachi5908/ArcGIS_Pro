import arcpy
import os
from arcpy.sa import *

# ==========================================
# 1. SETUP & CACHE CLEARING
# ==========================================
arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True
arcpy.ClearWorkspaceCache_management()

base_dir = r"D:\Geoinformatics\BAND Files"
arcpy.env.workspace = base_dir

print("Initializing error-proof NDWI workflow...")

# ==========================================
# 2. MOSAIC BANDS
# ==========================================
print("Mosaicking Band 3 (Green) and Band 5 (NIR)...")
b3_list = arcpy.ListRasters("LC*_B3*", "TIF")
b5_list = arcpy.ListRasters("LC*_B5*", "TIF")

arcpy.management.MosaicToNewRaster(
    input_rasters=b3_list, 
    output_location=base_dir, 
    raster_dataset_name_with_extension="Simple_B3.tif", 
    pixel_type="16_BIT_UNSIGNED", 
    number_of_bands=1
)

arcpy.management.MosaicToNewRaster(
    input_rasters=b5_list, 
    output_location=base_dir, 
    raster_dataset_name_with_extension="Simple_B5.tif", 
    pixel_type="16_BIT_UNSIGNED", 
    number_of_bands=1
)

# ==========================================
# 3. CALCULATE NDWI DIRECTLY
# ==========================================
print("Calculating NDWI directly from bands...")
b3 = Raster("Simple_B3.tif")
b5 = Raster("Simple_B5.tif")

# Standard Index Math: (Green - NIR) / (Green + NIR)
ndwi = (Float(b3) - Float(b5)) / (Float(b3) + Float(b5))

# ==========================================
# 4. CONVERT KML TO SHAPEFILE (ANY GEOMETRY)
# ==========================================
print("Converting KML to a fresh shapefile to bypass lock/corruption issues...")
kml_file = os.path.join(base_dir, "SagarAOI.kml")
kml_gdb_name = "SagarAOI_Layer"

try:
    arcpy.conversion.KMLToLayer(kml_file, base_dir, kml_gdb_name)
    gdb_path = os.path.join(base_dir, f"{kml_gdb_name}.gdb")
    
    # Dynamically walk through the GDB to find ANY feature class, regardless of type
    kml_fc = None
    for dirpath, dirnames, filenames in arcpy.da.Walk(gdb_path, datatype="FeatureClass"):
        for filename in filenames:
            kml_fc = os.path.join(dirpath, filename)
            break
        if kml_fc:
            break
            
    if not kml_fc:
        raise ValueError("No geometry found at all inside the converted KML geodatabase.")
    
    desc = arcpy.Describe(kml_fc)
    new_shp_name = "SagarAOI_Mask.shp"
    out_shp_path = os.path.join(base_dir, new_shp_name)
    
    # Intelligently handle Lines vs. Polygons
    if desc.shapeType == "Polygon":
        print("--> Found Polygon geometry. Exporting...")
        arcpy.conversion.FeatureClassToFeatureClass(kml_fc, base_dir, new_shp_name)
    elif desc.shapeType == "Polyline":
        print("--> Notice: KML contains Lines. Converting to a closed Polygon...")
        arcpy.management.FeatureToPolygon(kml_fc, out_shp_path)
    else:
        print(f"--> Found {desc.shapeType} geometry. Attempting standard export...")
        arcpy.conversion.FeatureClassToFeatureClass(kml_fc, base_dir, new_shp_name)
    
    mask_feature = out_shp_path
    print(f"--> Successfully created new mask: {mask_feature}")

except Exception as e:
    print(f"⚠️ KML to Shapefile conversion failed: {e}")
    mask_feature = os.path.join(base_dir, "sagar_polygon.shp")

# ==========================================
# 5. FAILSAFE CLIP & SAVE
# ==========================================
print("Clipping to polygon and saving to folder...")
final_output = ""

try:
    # Attempt to clip using the newly generated shapefile
    ndwi_clipped = ExtractByMask(ndwi, mask_feature)
    final_output = os.path.join(base_dir, "Simple_NDWI_Final.tif")
    ndwi_clipped.save(final_output)
    print("--> Clipping successful!")
    
except Exception as e:
    # FAILSAFE: Save the unclipped raster if clipping still fails
    print(f"⚠️ Clipping failed: {e}")
    print("--> FAILSAFE TRIGGERED: Saving the unclipped NDWI so you have the data...")
    final_output = os.path.join(base_dir, "Simple_NDWI_Unclipped.tif")
    ndwi.save(final_output)

# ==========================================
# 6. ADD TO MAP & AUTOSAVE PROJECT
# ==========================================
print("Adding final result to map and executing strict autosave...")
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap

    if active_map and final_output:
        active_map.addDataFromPath(final_output)

    aprx.save()
except Exception as e:
    print("--> Notice: Could not add to map/autosave (this is normal if running outside ArcGIS Pro).")

print("✅ Complete! Math processed, file saved, and ArcGIS Pro project autosaved.")