# Preprocess the survey ZIP files by unzipping only archives not yet extracted.

# The script scans an input directory for .zip files, checks whether each archive
# already appears extracted in the output directory, and extracts only the ones
# that are missing.

import zipfile
from pathlib import Path

# Normalize ZIP member paths to use forward slashes.
def normalized_member_path(member_name: str) -> Path:
    return Path(member_name.replace("\\", "/"))

# Check if a ZIP archive has already been extracted. 
# Return True if all non-directory members of the ZIP archive already exist in the output directory.
def is_zip_already_extracted(zip_path: Path, output_dir: Path) -> bool:
    # Return False if the ZIP archive is invalid or empty.
    try:
        # Loop through the archive to determine if there are files (not directories).
        with zipfile.ZipFile(zip_path, "r") as archive:
            file_members = [
                normalized_member_path(info.filename)
                for info in archive.infolist()
                if not info.is_dir() 
            ]
    except zipfile.BadZipFile:
        return False
    # Are there no files?
    if not file_members:
        return False

    # Check if each file member exists in the output directory.
    # Return False if any file member is missing.
    for member in file_members:
        if not (output_dir / member).exists():
            return False

    # The files are already extracted.
    return True 

# Preprocess the survey ZIP files by extracting only the ones not yet extracted.
# Return True if at least one new ZIP archive was extracted, False otherwise.
def preprocess_surveys(input_dir: Path, output_dir: Path) -> bool:
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"Input directory does not exist: {input_dir}")
        return False

    # make the output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get a sorted list of all ZIP files in the input directory.
    zip_files = sorted(input_dir.glob("*.zip"))
    # Check if there are zip files in the directory.
    if not zip_files:
        print(f"No ZIP files found in {input_dir}")
        return False

    # Initialize result counters.
    extracted = 0
    skipped = 0

    # Process each ZIP file in the directory.
    for zip_path in zip_files:
        # Check if the ZIP file has already been extracted.
        if is_zip_already_extracted(zip_path, output_dir):
            skipped += 1
            print(f"Skip  {zip_path.name}: already extracted")
            continue # loop again

        # Extract the zip archive to the output directory.
        try:
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(output_dir)
            extracted += 1 # add one for extracting
            print(f"Unzip    {zip_path.name} -> {output_dir}")
        except (zipfile.BadZipFile, OSError) as exc:
            skipped += 1 # error, so add one for skipping
            print(f"Skip  {zip_path.name}: {exc}")

    # Print the results of the preprocessing unzipping.
    print()
    print(f"Processed {len(zip_files)} ZIP file(s).")
    print(f"Unzipped: {extracted}")
    print(f"Skipped:   {skipped}")
    print(f"Output:    {output_dir}")

    return extracted > 0

# Main entry point of the script for unit testing and development.
def main() -> int:
    # Set run parameters here.
    input_dir = Path("downloaded_surveys")
    output_dir = Path("preprocessed_surveys")

    extracted_any = preprocess_surveys(input_dir=input_dir, output_dir=output_dir)

    if extracted_any:
        print("At least one new ZIP was extracted.")
    else:
        print("No new ZIP files needed extraction.")

    return 0

if __name__ == "__main__":
    exit(main())
