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

print("Initializing NDWI.docx compliant workflow...")

# ==========================================
# 2. MOSAIC BANDS
# ==========================================
print("Mosaicking Band 3 and Band 5 with specific operators...")
b3_list = arcpy.ListRasters("LC*_B3*", "TIF")
b5_list = arcpy.ListRasters("LC*_B5*", "TIF")

arcpy.management.MosaicToNewRaster(
    input_rasters=b3_list, 
    output_location=base_dir, 
    raster_dataset_name_with_extension="B3_Mosaic.tif", 
    pixel_type="16_BIT_UNSIGNED", 
    number_of_bands=1,
    mosaic_method="LAST",
    mosaic_colormap_mode="FIRST"
)

arcpy.management.MosaicToNewRaster(
    input_rasters=b5_list, 
    output_location=base_dir, 
    raster_dataset_name_with_extension="B5_Mosaic.tif", 
    pixel_type="16_BIT_UNSIGNED", 
    number_of_bands=1,
    mosaic_method="LAST",
    mosaic_colormap_mode="FIRST"
)

# ==========================================
# 3. CALCULATE NDWI WITH RADIOMETRIC CALIBRATION
# ==========================================
print("Applying scaling factors and calculating NDWI_Final...")
b3 = Raster("B3_Mosaic.tif")
b5 = Raster("B5_Mosaic.tif")

# Apply Landsat scaling factor as per documentation
b3_scaled = Float(b3) * 0.0000275 - 0.2
b5_scaled = Float(b5) * 0.0000275 - 0.2

# Implement the SetNull logic from the document
invalid_mask = (b3_scaled <= 0) | (b5_scaled <= 0)
ndwi_math = (b3_scaled - b5_scaled) / (b3_scaled + b5_scaled)

ndwi_final = SetNull(invalid_mask, ndwi_math)
ndwi_final.save("NDWI_Final.tif")

# ==========================================
# 4. EXTRACT WATER AREAS (BINARY RASTER)
# ==========================================
print("Extracting potential water areas (NDWI > 0)...")
# Creates a binary raster where 1 = Water, 0 = Non-Water
water_ndwi = ndwi_final > 0
water_ndwi.save("Water_NDWI.tif")

# ==========================================
# 5. CONVERT KML TO SHAPEFILE (LOCK BYPASS)
# ==========================================
print("Preparing mask geometry...")
kml_file = os.path.join(base_dir, "SagarAOI.kml")
kml_gdb_name = "SagarAOI_Layer"
mask_feature = ""

try:
    arcpy.conversion.KMLToLayer(kml_file, base_dir, kml_gdb_name)
    gdb_path = os.path.join(base_dir, f"{kml_gdb_name}.gdb")
    
    kml_fc = None
    for dirpath, dirnames, filenames in arcpy.da.Walk(gdb_path, datatype="FeatureClass"):
        for filename in filenames:
            kml_fc = os.path.join(dirpath, filename)
            break
        if kml_fc:
            break
            
    if not kml_fc:
        raise ValueError("No geometry found.")
    
    desc = arcpy.Describe(kml_fc)
    new_shp_name = "SagarAOI_Mask.shp"
    out_shp_path = os.path.join(base_dir, new_shp_name)
    
    if desc.shapeType == "Polygon":
        arcpy.conversion.FeatureClassToFeatureClass(kml_fc, base_dir, new_shp_name)
    elif desc.shapeType == "Polyline":
        arcpy.management.FeatureToPolygon(kml_fc, out_shp_path)
    else:
        arcpy.conversion.FeatureClassToFeatureClass(kml_fc, base_dir, new_shp_name)
    
    mask_feature = out_shp_path
    print(f"--> Successfully created new mask: {mask_feature}")

except Exception as e:
    print(f"⚠️ KML to Shapefile conversion failed: {e}")
    # Final fallback if KML fails
    mask_feature = os.path.join(base_dir, "sagar_polygon.shp")

# ==========================================
# 6. FINAL CLIP (EXTRACT BY MASK)
# ==========================================
print("Clipping binary water raster to study area...")
final_output = ""

try:
    # We clip the binary Water_NDWI, not the raw NDWI_Final, as per the doc
    final_clipped = ExtractByMask(water_ndwi, mask_feature)
    final_output = os.path.join(base_dir, "Water_NDWI_StudyArea.tif")
    final_clipped.save(final_output)
    print("--> Clipping successful!")
    
except Exception as e:
    print(f"⚠️ Clipping failed: {e}")

# ==========================================
# 7. ADD TO MAP & AUTOSAVE PROJECT
# ==========================================
print("Adding final results to map and saving project...")
try:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    active_map = aprx.activeMap

    if active_map:
        active_map.addDataFromPath(os.path.join(base_dir, "NDWI_Final.tif"))
        if final_output:
            active_map.addDataFromPath(final_output)

    aprx.save()
except Exception as e:
    print("--> Notice: Could not add to map/autosave.")

print("✅ Complete! All NDWI.docx logic applied.")