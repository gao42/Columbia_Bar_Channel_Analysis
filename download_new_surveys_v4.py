# Download only new surveys that are not already downloaded.

# This script queries surveys in a bounding box, filters by text (default: MCR),
# checks what has already been downloaded (ZIPs), and downloads only new
# surveys.

import re
import shutil
from datetime import date, datetime
from pathlib import Path
import requests

# Define the URL of the survey service.
SERVICE_URL = (
    "https://services7.arcgis.com/n1YM8pTrFmm7L4hs/ArcGIS/rest/services/"
    "eHydro_Survey_Data/FeatureServer/0/query"
)

# Define a pattern to extract dates in YYYYMMDD format from 
# survey ID name string.
def parse_yyyymmdd(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        print(f"invalid date '{value}'. Expected format: YYYYmmdd")
        exit(1)

# Extract the survey date from the survey ID string.
# Return the date or None if it cannot be extracted.
DATE_TOKEN_PATTERN = re.compile(r"(\d{8})") # exactly 8 digits for the date
def extract_survey_date(survey_id: str) -> date | None:
    match = DATE_TOKEN_PATTERN.search(survey_id) # match the date token
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date() # parse the date token
    except ValueError:
        return None

# Query a page of surveys within the bounding box.
# Return a list of survey features.
def query_surveys_page(
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
    page_size: int,
    offset: int,
    survey_filter: str,
) -> list[dict]:
    safe_filter = survey_filter.upper().replace("'", "''")
    # define the query parameters
    params = {
        "f": "json",
        "where": (
            f"UPPER(surveyjobidpk) LIKE '%{safe_filter}%' "
            f"OR UPPER(sdsfeaturename) LIKE '%{safe_filter}%'"
        ),
        "geometry": f"{xmin},{ymin},{xmax},{ymax}", # bounding box coordinates
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "returnGeometry": "false",
        "outFields": "surveyjobidpk,sourcedatalocation,sdsfeaturename,surveytype,sourceagency",
        "orderByFields": "surveyjobidpk ASC",
        "resultRecordCount": page_size,
        "resultOffset": offset,
    }
    # Send the request to the survey service.
    response = requests.get(SERVICE_URL, params=params, timeout=30)
    # Check for HTTP errors.
    response.raise_for_status()
    # Parse the JSON response.
    payload = response.json()
    # Return the list of survey features.
    return payload.get("features", [])

# Download a file from a URL to the specified destination.
def download_file(url: str, destination: Path) -> None:
    # Download the file from the URL to the specified destination.
    with requests.get(url, stream=True, timeout=60) as response:
        # Check for HTTP errors using with response.
        response.raise_for_status()
        # Create the parent directories if they don't exist.
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Write the response content to the destination file.
        with destination.open("wb") as output_file:
            shutil.copyfileobj(response.raw, output_file)

# Load the set of downloaded survey name IDs from the output directory.
# Return a set of downloaded survey name IDs.
def load_downloaded_name_ids(outdir: Path) -> set[str]:
    # Create an empty set of string values.
    downloaded: set[str] = set()

    if outdir.exists():
        # Add all existing zip files in the output directory 
        # to the set of downloaded surveys.
        for zip_path in outdir.glob("*.zip"): # iterate through the zip files
            downloaded.add(zip_path.stem.upper())

    return downloaded

# Check if not downloaded and download surveys within the 
# defined bounding box.
def check_and_download_surveys(
    bbox: tuple[float, float, float, float],
    outdir: Path,
    survey_filter: str = "MCR",
    limit: int = 25,
    start_date: date | None = None,
    end_date: date | None = None, ) -> bool:

    # Unpack the bounding box coordinates.
    xmin, ymin, xmax, ymax = bbox
    # Convert the survey filter to uppercase and strip whitespace.
    survey_filter = survey_filter.upper().strip()

    # Verify input parameters are valid.
    if limit < 1:
        print("--limit must be at least 1")
        exit(1)
    if not survey_filter:
        print("--survey-filter cannot be empty")
        exit(1)
    if start_date and end_date and start_date > end_date:
        print("--start-date must be earlier than or equal to --end-date")
        exit(1)

    # Make the output directory if it doesn't exist.
    outdir.mkdir(parents=True, exist_ok=True)

    # Load the set of already downloaded survey name IDs.
    known_downloaded = load_downloaded_name_ids(outdir)
    # How many surveys do we already have.
    print(f"Known downloaded surveys: {len(known_downloaded)}")

    # Initialize counters.
    downloaded_now = 0
    skipped = 0
    offset = 0
    page_size = 200
    seen_name_ids: set[str] = set()

    # Download surveys until the limit is reached (can't go forever).
    while downloaded_now < limit:
        # Query a page of surveys based on the bounding box and filter.
        features = query_surveys_page(
            xmin, ymin, xmax, ymax, page_size, offset, survey_filter
        )

        # Check the returned set of features.
        if not features:
            break
        
        # For each set of feature, inspect the attributes.
        for feature in features:
            # Check if we have reached the download limit.
            if downloaded_now >= limit:
                break

            attributes = feature.get("attributes", {})
            survey_id = (attributes.get("surveyjobidpk") or "").strip()
            url = (attributes.get("sourcedatalocation") or "").strip()
            name = str(attributes.get("sdsfeaturename") or "")
            #survey_type = str(attributes.get("surveytype") or "")
            #source_agency = str(attributes.get("sourceagency") or "")
            survey_date = extract_survey_date(survey_id) if survey_id else None
            #survey_date_text = survey_date.isoformat() if survey_date else ""

            if not survey_id:
                skipped += 1
                print("Skip:  <missing id>: missing surveyjobidpk")
                continue # loop again

            # Normalize the survey ID for consistent comparison.
            survey_id_upper = survey_id.upper()
            if survey_id_upper in seen_name_ids: # have already seen this survey ID
                continue # loop again
            # Mark this survey ID as seen.
            seen_name_ids.add(survey_id_upper)

            # Apply the survey filter to the feature data.
            if survey_filter not in survey_id_upper and survey_filter not in name.upper():
                skipped += 1
                continue # loop again

            # Apply the date filter to the feature data.
            if start_date or end_date:
                if not survey_date:
                    skipped += 1
                    print(f"Skip:  {survey_id}: could not parse YYYYmmdd date from survey ID")
                    continue # loop again

                # Check if the survey date is before the start date.
                if start_date and survey_date < start_date:
                    skipped += 1
                    print(
                        f"Skip:  {survey_id}: survey date {survey_date.isoformat()} is before start date"
                    )
                    continue # loop again

                # Check if the survey date is after the end date.
                if end_date and survey_date > end_date:
                    skipped += 1
                    print(
                        f"Skip:  {survey_id}: survey date {survey_date.isoformat()} is after end date"
                    )
                    continue # loop again

            # Check if the survey has already been downloaded.
            if survey_id_upper in known_downloaded:
                print(f"Skip:  {survey_id}: already downloaded")
                continue # loop again

            # Check if the download URL is available.
            if not url:
                skipped += 1
                print(f"Skip:  {survey_id}: missing download URL")
                continue # loop again

            # Determine the destination file path.
            destination = outdir / f"{survey_id}.zip"

            # If we made it here, try and download the survey.
            try:
                download_file(url, destination)
            except (requests.RequestException, OSError) as exc:
                skipped += 1
                message = str(exc)
                print(f"Skip:  {survey_id}: {message}")
                continue # loop if an error

            # Mark the survey as downloaded.
            downloaded_now += 1
            known_downloaded.add(survey_id_upper)
            print(f"New:   {survey_id} -> {destination}")

        # Update the offset for the next batch of features.
        offset += len(features)

    # Print a summary of the downloading results.
    print()
    print(f"Downloaded {downloaded_now} new survey(s); skipped {skipped}.")
    return (downloaded_now > 0) # return True if any new surveys were downloaded, False otherwise

# Main entry point of the script for unit testing and development.
def main() -> int:
    # Set run parameters here.
    bbox = (-124.2, 46.0, -123.6, 46.6)
    outdir = Path("surveys")
    survey_filter = "MCR"
    limit = 25
    start_date = parse_yyyymmdd("20240101")
    end_date = parse_yyyymmdd("20251231")

    downloaded = check_and_download_surveys(
        bbox=bbox,
        outdir=outdir,
        survey_filter=survey_filter,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
    )

    if downloaded:
        print("At least one new survey was downloaded.")
    else:
        print("No new surveys were downloaded.")

    return 0


if __name__ == "__main__":
    exit(main())
