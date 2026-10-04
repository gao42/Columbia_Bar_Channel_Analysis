# Generate Columbia Bar Change Reports

import os
from pathlib import Path
import arcpy

# Function for exporting a single report to a PDF
def export_single_report(
    project_path,
    layout_name,
    raster_path,
    pdf_path,
    source_dir_name,
    zoom_out_factor=5,
    resolution=300,
) -> int:
    # Check if the project file and raster exist.
    if not os.path.isfile(project_path):
        print(f"Project file not found: {project_path}")
        return 1
    if not arcpy.Exists(raster_path):
        print(f"Filtered raster not found: {raster_path}")
        return 1

    # Open the ArcGIS Pro project with mp tool.
    aprx = arcpy.mp.ArcGISProject(project_path)

    # Get the layout by name.
    layouts = aprx.listLayouts(layout_name)
    if not layouts:
        print(f'Layout "{layout_name}" was not found in {project_path}')
        return 1

    # Get the first layout from the list.
    layout = layouts[0]

    # Update the "Data" text element with the source directory name.
    data_elements = layout.listElements("TEXT_ELEMENT", "Data")
    if data_elements:
        data_elements[0].text = f"Survey Data Window: {source_dir_name}"
    else:
        print('SKIP  Layout text element named "Data" was not found.')

    # Get the map frame by name "Extent" or the first one if not found.
    map_frames = layout.listElements("MAPFRAME_ELEMENT", "Extent")
    if map_frames:
        # Use the first map frame named "Extent".
        map_frame = map_frames[0]
    else:
        # Could not find a map frame named "Extent", use the first one.
        map_frames = layout.listElements("MAPFRAME_ELEMENT")
        if not map_frames:
            print(f'No map frame was found in layout "{layout_name}"')
            return 1
        map_frame = map_frames[0]

    # Get the map object from the map frame.
    map_obj = map_frame.map

    # Remove existing raster layers from the map.
    for layer in map_obj.listLayers():
        if layer.isRasterLayer:
            map_obj.removeLayer(layer)

    # Add the filtered raster layer to the map.
    filtered_layer = map_obj.addDataFromPath(raster_path)

    # Positions the new raster before the first layer in the map.
    layers = map_obj.listLayers()
    if filtered_layer and layers:
        map_obj.moveLayer(layers[0], filtered_layer, "BEFORE")

    # Set the map frame extent to the raster extent and apply zoom out factor.
    map_frame.camera.setExtent(arcpy.Describe(raster_path).extent)
    if zoom_out_factor and zoom_out_factor > 1:
        map_frame.camera.scale = map_frame.camera.scale * zoom_out_factor

    # Save the project and export the layout to a PDF.
    aprx.save()
    layout.exportToPDF(pdf_path, resolution=resolution)

    print(f"Report exported to: {pdf_path}")
    return 0


def gen_report(
    analyzed_dir,
    reports_dir,
    project_path,
    layout_name,
    zoom_out_factor=5,
    resolution=300,
):
    
    # Make the reports directory if it doesn't exist
    os.makedirs(reports_dir, exist_ok=True)

    if not os.path.isdir(analyzed_dir):
        print(f"Analyzed surveys directory not found: {analyzed_dir}")
        return 1

    # Get the list of analysis runs from the analyzed directory.
    analysis_runs = sorted(
        entry for entry in os.listdir(analyzed_dir)
        if os.path.isdir(os.path.join(analyzed_dir, entry))
    )

    # Check if any analysis runs were found.
    if not analysis_runs:
        print(f"No analysis runs found in {analyzed_dir}")
        return 0
   
    # Initialize counters.
    generated = 0
    skipped_existing = 0
    skipped_missing_raster = 0
    failed = 0

    # Loop through each analysis run and generate reports (if not already existing).
    for source_dir_name in analysis_runs:
        workspace_dir = os.path.join(analyzed_dir, source_dir_name)
        raster_path = os.path.join(workspace_dir, "bathy_change_filtered.tif")
        pdf_path = os.path.join(
            reports_dir,
            f"Columbia_Bar_Change_Report_{source_dir_name}.pdf"
        )

        # Check if a report has already been created.
        if os.path.isfile(pdf_path):
            skipped_existing += 1
            print(f"SKIP  Existing report: {pdf_path}")
            continue # loop again

        # Check if the analysis filtered raster exists.
        if not arcpy.Exists(raster_path):
            skipped_missing_raster += 1
            print(f"SKIP  Missing raster: {raster_path}")
            continue # loop again
        
        # Create and export the single report to PDF.
        result = export_single_report(
            project_path=project_path,
            layout_name=layout_name,
            raster_path=raster_path,
            pdf_path=pdf_path,
            source_dir_name=source_dir_name,
            zoom_out_factor=zoom_out_factor,
            resolution=resolution,
        )

        if result == 0:
            generated += 1
        else:
            failed += 1

    # Print summary of the report generation process.
    print()
    print(f"Analysis runs found: {len(analysis_runs)}")
    print(f"Reports generated: {generated}")
    print(f"Skipped (already exists): {skipped_existing}")
    print(f"Skipped (missing raster): {skipped_missing_raster}")
    print(f"Failed: {failed}")

    if failed > 0:
        return 1 # return 1 if any failed
    return 0

# Main entry point of the script for unit testing and development.
def main():
    # Set run parameters here.
    base_dir = Path(__file__).resolve().parent
    analyzed_dir = base_dir / "analyzed_surveys"
    reports_dir = base_dir / "analysis_reports"

    project_path = base_dir / "Columbia_Bar_Analysis.aprx"
    layout_name = "ReportLayout"
    zoom_out_factor = 5
    resolution = 300

    return gen_report(
        analyzed_dir=analyzed_dir,
        reports_dir=reports_dir,
        project_path=project_path,
        layout_name=layout_name,
        zoom_out_factor=zoom_out_factor,
        resolution=resolution,
    )


if __name__ == "__main__":
    exit(main())