# Analyze surveys by comparing bathymetry rasters from different dates.

from pathlib import Path

import arcpy
from arcpy.sa import *
import os
import re
from datetime import date

# Utility function for adding months to a date
def add_months(dateVal, months):
    year = dateVal.year + (dateVal.month - 1 + months) // 12 # fractional year
    month = (dateVal.month - 1 + months) % 12 + 1 # number of months within the year
    day = min(dateVal.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]) # day within the month
    return date(year, month, day)

# Utility function for finding dated geodatabases
def find_dated_gdbs(root_dir):
    gdb_entries = [] # list of the geodatabases
    date_pattern = re.compile(r"(\d{8})") 

    # Loop through the directory tree and build a list of the avaialable 
    # geodatabases
    for dirpath, dirnames, _ in os.walk(root_dir):
        for dirname in dirnames:
            if not dirname.lower().endswith(".gdb"):
                continue # not a geodatabase loop again

            gdb_path = os.path.join(dirpath, dirname)
            match = date_pattern.search(dirname) # search the dir name
            if not match:
                match = date_pattern.search(os.path.basename(dirpath)) # search the file name
            if not match:
                continue # loop again

            # Extract the date from the directory name or its parent directory.
            ds_date = date.fromisoformat(
                f"{match.group(1)[0:4]}-{match.group(1)[4:6]}-{match.group(1)[6:8]}"
            )
            gdb_entries.append((ds_date, gdb_path)) # add to the list

    return sorted(gdb_entries, key=lambda x: x[0])

# Main function to analyze surveys by comparing bathymetry rasters from different dates.
def analyze_surveys(
    months_diff,
    source_dir,
    output_dir,
    cell_size=5,
    threshold=0.25,
):
    # Make the output directory if it doesn't exist.
    os.makedirs(output_dir, exist_ok=True)

    # Check if the source directory of surveys exists.
    if not os.path.isdir(source_dir):
        print(f"Surveys folder not found: {source_dir}")
        exit(1)

    # Find all dated geodatabases in the source directory.
    dated_gdbs = find_dated_gdbs(source_dir)
    # Check that we at least have two surveys.
    if len(dated_gdbs) < 2:
        print(f"Need at least 2 dated .gdb folders in {source_dir}; found {len(dated_gdbs)}.")
        exit(1)

    # Based on the latest survey and month diff determine a target date.
    latest_date, latest_gdb = dated_gdbs[-1] # the end of the list
    target_date = add_months(latest_date, -months_diff)

    # Pick the survey nearest to the target, excluding the latest survey itself.
    comparison_candidates = dated_gdbs[:-1] # all but the latest survey
    if not comparison_candidates:
        print("No comparison survey available after selecting latest survey.")
        exit(1)

    # Pick the survey closest to the target date.
    compare_date, compare_gdb = min(
        comparison_candidates,
        key=lambda x: abs((x[0] - target_date).days)
    )
    
    # Define paths to the latest and past bathymetry rasters.
    raster_latest = os.path.join(latest_gdb, "Bathymetry_Raster")
    raster_past = os.path.join(compare_gdb, "Bathymetry_Raster")

    # Check that ArcPy can see the rasters.
    if not arcpy.Exists(raster_latest):
        print(f"Bathymetry_Raster not found in latest gdb: {latest_gdb}")
        exit(1)
    if not arcpy.Exists(raster_past):
        print(f"Bathymetry_Raster not found in comparison gdb: {compare_gdb}")
        exit(1)

    # Print summary of the surveys being compared.
    print(f"Latest survey: {latest_date.isoformat()} -> {latest_gdb}")
    print(f"Target comparison date ({months_diff} months in the past): {target_date.isoformat()}")
    print(f"Comparison survey: {compare_date.isoformat()} -> {compare_gdb}")

    run_output_dir = os.path.join(
        output_dir,
        f"{compare_date.strftime('%Y%m%d')}_{latest_date.strftime('%Y%m%d')}_{months_diff}"
    )
    os.makedirs(run_output_dir, exist_ok=True)
    arcpy.env.workspace = run_output_dir
    print(f"Run output directory: {run_output_dir}")

    # Define the output coordinate system.
    output_cs = arcpy.SpatialReference(26910)   # UTM Zone 10N NAD83

    ## Step 1: Project the rasters to a common coordinate system ##

    print("Projecting rasters...")

    r_past_proj = "dem_past_proj.tif"
    r_latest_proj = "dem_latest_proj.tif"

    # Project the past raster to the output coordinate system.
    arcpy.management.ProjectRaster(
        raster_past,
        r_past_proj,
        output_cs,
        "BILINEAR"
    )
    # Project the latest raster to the output coordinate system.
    arcpy.management.ProjectRaster(
        raster_latest,
        r_latest_proj,
        output_cs,
        "BILINEAR"
    )

    ## Step 2: Align the later raster to the early raster ##

    arcpy.env.snapRaster = r_past_proj
    arcpy.env.cellSize = cell_size

    r_latest_align = "dem_latest_align.tif"

    # Resample the latest raster to align with the past raster.
    arcpy.management.Resample(
        r_latest_proj,
        r_latest_align,
        cell_size,
        "BILINEAR"
    )

    ## Step 3: Find the overlapping extent of the two rasters ##

    desc1 = arcpy.Describe(r_past_proj)
    desc2 = arcpy.Describe(r_latest_align)

    # Determine the extent of the overlapping area.
    xmin = max(desc1.extent.XMin, desc2.extent.XMin)
    ymin = max(desc1.extent.YMin, desc2.extent.YMin)
    xmax = min(desc1.extent.XMax, desc2.extent.XMax)
    ymax = min(desc1.extent.YMax, desc2.extent.YMax)

    arcpy.env.extent = arcpy.Extent(xmin, ymin, xmax, ymax)

    ## Step 4: Compute the raw change raster ##

    print("Computing change raster...")

    # Determine the delta change.
    change = Raster(r_latest_align) - Raster(r_past_proj)

    # Save the results.
    change.save("bathy_change_raw.tif") 

    ## Step 5: Filter the raw change raster ##

    filtered = Con(
        Abs(change) >= threshold,
        change
    )

    # Save the results.
    filtered.save("bathy_change_filtered.tif")

    # Create deposition and erosion rasters by filtering the change raster 
    # around zero.
    deposition = Con(filtered > 0, filtered)
    erosion = Con(filtered < 0, filtered)

    # Save the results.
    deposition.save("deposition.tif")
    erosion.save("erosion.tif")

    print("Finished generating analysis rasters.")

# Main entry point of the script for unit testing and development.
def main() -> int: 

    ## parameter definitions ##
    analyze_source_dir = Path("processed_surveys")
    analyze_output_dir = Path("analyzed_surveys")
    
    #arcpy.CheckOutExtension("Spatial")
    arcpy.env.workspace = str(analyze_output_dir)
    arcpy.env.overwriteOutput = True

    months_diff = 12

    if months_diff <= 0:
        print("months_diff must be a positive integer")
        exit(1)

    analyze_surveys(
        months_diff=months_diff,
        source_dir=str(analyze_source_dir),
        output_dir=str(analyze_output_dir),
    )

    return 0

if __name__ == "__main__":
    exit(main())