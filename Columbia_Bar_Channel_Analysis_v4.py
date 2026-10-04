## Columbia Bar Channel Analysis - Execution of the workflow

import os
from pathlib import Path
from datetime import date

import arcpy

from download_new_surveys_v4 import parse_yyyymmdd
from download_new_surveys_v4 import check_and_download_surveys
from preprocess_surveys_v2 import preprocess_surveys
from analyze_surveys_v13 import analyze_surveys
from generate_report_v5 import gen_report

#---- Define the necessary parameters ----
# download surveys parameters
bbox = (-124.2, 46.0, -123.6, 46.6) # the lat lon box of the survey query
download_dir = Path("downloaded_surveys") # the download file location
survey_filter = "MCR" # Mouth of the Columbia River survey filter
limit = 25 # max number of surveys to download 
start_date = parse_yyyymmdd("20240101") # starting date of survey time window
today = date.today().strftime("%Y%m%d") # get today's date
end_date = parse_yyyymmdd(today) # ending date of survey time window

# preprocess survey parameters
preprocess_input_dir = download_dir
preprocess_output_dir = Path("preprocessed_surveys")

## analyze surveys parameters
analyze_source_dir = preprocess_output_dir
analyze_output_dir = Path("analyzed_surveys")
#arcpy.CheckOutExtension("Spatial")
arcpy.env.workspace = str(analyze_output_dir)
arcpy.env.overwriteOutput = True

# report generated parameters
base_dir = os.path.dirname(os.path.abspath(__file__))
analyzed_dir = os.path.join(base_dir, "analyzed_surveys")
reports_dir = os.path.join(base_dir, "analysis_reports")

project_path = os.path.join(base_dir, "Columbia_Bar_Analysis.aprx")
layout_name = "ReportLayout"
resolution = 300


#---- Step 1: download new surveys ----
# Using the download_new_surveys_v4.py script module, download the
# available surveys from the USACE database for the specified time window.
downloaded = check_and_download_surveys(
    bbox=bbox,
    outdir=download_dir,
    survey_filter=survey_filter,
    limit=limit,
    start_date=start_date,
    end_date=end_date,
)

if downloaded:
    print("At least one new survey was downloaded.")
else:
    print("No new surveys were downloaded.")


#---- Step 2: pre-process new surveys ----
# Using the preprocess_surveys_v2.py script module, pre-process the 
# the available downloaded surveys.
processed = preprocess_surveys(input_dir=preprocess_input_dir, output_dir=preprocess_output_dir)

if processed:
    print("At least one new ZIP was processed.")
else:
    print("No new ZIP files needed processing.")


#---- Step 3: analyze new surveys ----
# Using the analyze_surveys_v13.py script module, analyze the pre-processed surveys
# for 1, 6, and 12 months time difference in surveys analysis.

# 1 months time difference in surveys analysis (or at least 1 month)
months_diff = 1
analyze_surveys(
    months_diff=months_diff,
    source_dir=str(analyze_source_dir),
    output_dir=str(analyze_output_dir),
)

# 6 months time difference in surveys analysis
months_diff = 6
analyze_surveys(
    months_diff=months_diff,
    source_dir=str(analyze_source_dir),
    output_dir=str(analyze_output_dir),
)

## 12 months time difference in surveys analysis
months_diff = 12
analyze_surveys(
    months_diff=months_diff,
    source_dir=str(analyze_source_dir),
    output_dir=str(analyze_output_dir),
)

#---- Step 4: generate reports ----
# Using the generate_report_v5.py script module generate the reports 
# for the analysis runs. 
gen_report(
    analyzed_dir=analyzed_dir,
    reports_dir=reports_dir,
    project_path=project_path,
    layout_name=layout_name,
    resolution=resolution,
)
   