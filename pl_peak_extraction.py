import pandas as pd
import numpy as np
import os

# --- Configuration for PL Peak Extraction ---
# Folder where your raw PL spectrum files are located
RAW_PL_DATA_FOLDER = 'PL_Spectra_Raw'

# Output file where the extracted peak data will be saved
OUTPUT_PEAK_DATA_FILE = 'extracted_pl_peaks.csv'  # Can be .csv or .xlsx
OUTPUT_FILE_TYPE = 'csv'  # 'csv' or 'excel'

# Configuration for reading individual PL spectrum files
PL_WAVELENGTH_COL_NAME = 'lambda [nm]'  # Exact column name for wavelength in your PL files
PL_INTENSITY_COL_NAME = 'intensity [a.u.]'  # Exact column name for intensity in your PL files

# Number of header/comment rows to skip before the actual data header row
# For your example: # lines (8) + data header (1) = 9 lines to skip if using header=0 on data line.
# If using names=[] and header=None, and comment='#', it's just the lines before data actually starts.
# Let's use comment='#', sep='\t', and names to get columns directly.
# The `pd.read_csv` `comment` argument handles lines starting with '#'.
# The `names` argument will assign the given column names.
# The actual header row 'lambda [nm]\intensity [a.u.]' will be the first row of data if no 'skiprows'.
# So we effectively skip everything until that line and then read that line as data columns.
# It seems safest to manually skip the fixed number of comment lines and then let pandas handle the actual data header.
# Let's refine this to skip *up to* the line that contains the column names.

# --- Helper Functions ---
def get_sample_id_from_filename(filename):
    """
    Extracts the sample ID from the PL spectrum filename.
    Assumes filename is like 'G25-023-center.csv' -> 'G25-023-center'
    Adjust this function if your naming convention is different.
    """
    base_name = os.path.splitext(filename)[0]  # Removes extension
    # Add more complex logic here if your sample ID is embedded differently,
    # e.g., if files are 'PL_RunX_SampleY.txt' and you want only 'SampleY'
    return base_name


def analyze_single_pl_file(file_path):
    """
    Reads a single PL spectrum file, extracts its peak wavelength and intensity.
    Handles metadata lines starting with '#'.
    """
    try:
        # Determine skiprows dynamically by finding the data header line
        skip_rows_count = 0
        with open(file_path, 'r') as f:
            for line in f:
                if PL_WAVELENGTH_COL_NAME in line and PL_INTENSITY_COL_NAME in line:
                    break  # Found the header line
                skip_rows_count += 1
            else:
                raise ValueError(
                    f"Could not find data header '{PL_WAVELENGTH_COL_NAME}\\t{PL_INTENSITY_COL_NAME}' in {file_path}")

        # Read the data section of the CSV
        # comment='#' will ignore lines starting with '#' *after* skiprows
        # header=skip_rows_count-1 because read_csv counts from 0, and we want the line before data as header
        # Using '\t' as separator as per your example. Adjust if it's space or comma.
        pl_spectrum_df = pd.read_csv(file_path, sep='\t', skiprows=skip_rows_count,
                                     names=[PL_WAVELENGTH_COL_NAME, PL_INTENSITY_COL_NAME],
                                     comment='#',
                                     header=None)  # names overrides header, header=None needed for skiprows

        # Convert to numeric, coercing errors to NaN
        pl_spectrum_df[PL_WAVELENGTH_COL_NAME] = pd.to_numeric(pl_spectrum_df[PL_WAVELENGTH_COL_NAME], errors='coerce')
        pl_spectrum_df[PL_INTENSITY_COL_NAME] = pd.to_numeric(pl_spectrum_df[PL_INTENSITY_COL_NAME], errors='coerce')

        # Drop any rows with non-numeric data
        pl_spectrum_df.dropna(subset=[PL_WAVELENGTH_COL_NAME, PL_INTENSITY_COL_NAME], inplace=True)

        if pl_spectrum_df.empty:
            print(f"  Warning: No valid numerical PL data found in {file_path}.")
            return None, None

        # Find the index of the maximum intensity
        max_intensity_idx = pl_spectrum_df[PL_INTENSITY_COL_NAME].idxmax()

        # Get the peak wavelength and intensity
        peak_w = pl_spectrum_df.loc[max_intensity_idx, PL_WAVELENGTH_COL_NAME]
        peak_i = pl_spectrum_df.loc[max_intensity_idx, PL_INTENSITY_COL_NAME]

        return peak_w, peak_i

    except FileNotFoundError:
        print(f"  Error: File not found: {file_path}")
        return None, None
    except pd.errors.EmptyDataError:
        print(f"  Error: File {file_path} is empty or contains no data.")
        return None, None
    except Exception as e:
        print(f"  Error processing {file_path}: {e}")
        return None, None


# --- Main Execution Flow for PL Peak Extraction ---
if __name__ == "__main__":
    print("--- Starting PL Peak Extractor Script ---")
    print(f"\nScanning raw PL files in: {RAW_PL_DATA_FOLDER}")

    processed_peaks_data = []

    # Iterate through all files in the raw PL data folder
    for filename in os.listdir(RAW_PL_DATA_FOLDER):
        if filename.endswith('.csv'):  # Or .txt, etc.
            sample_id = get_sample_id_from_filename(filename)
            file_path = os.path.join(RAW_PL_DATA_FOLDER, filename)

            print(f"Processing '{filename}' (Sample ID: {sample_id})...")
            peak_w, peak_i = analyze_single_pl_file(file_path)

            if peak_w is not None and peak_i is not None:
                processed_peaks_data.append({
                    'QW_Sample': sample_id,
                    'PL_Peak_Wavelength_nm': peak_w,
                    'PL_Peak_Intensity_au': peak_i
                })
                print(f"  Extracted Peak: Wavelength={peak_w:.2f} nm, Intensity={peak_i:.4f} a.u.")
            else:
                print(f"  Failed to extract peak for {sample_id}.")

    if not processed_peaks_data:
        print("\nNo PL peaks were successfully extracted. Check your raw data files and configuration.")
    else:
        # Create a DataFrame from the extracted peak data
        output_df = pd.DataFrame(processed_peaks_data)

        # Save the consolidated data to a CSV or Excel file
        if OUTPUT_FILE_TYPE == 'csv':
            output_df.to_csv(OUTPUT_PEAK_DATA_FILE, index=False)
        elif OUTPUT_FILE_TYPE == 'excel':
            try:
                output_df.to_excel(OUTPUT_PEAK_DATA_FILE, index=False, sheet_name='PL_Peaks')
            except ImportError:
                print("Error: 'openpyxl' not installed. Cannot save to Excel. Please run: pip install openpyxl")
                output_df.to_csv(OUTPUT_PEAK_DATA_FILE.replace('.xlsx', '.csv'), index=False)
                print(f"Saved to CSV instead: {OUTPUT_PEAK_DATA_FILE.replace('.xlsx', '.csv')}")

        print(f"\n--- PL Peak Extraction Complete ---")
        print(f"Extracted peaks for {len(processed_peaks_data)} samples.")
        print(f"Consolidated data saved to: {OUTPUT_PEAK_DATA_FILE}")
        print("\nFirst 5 rows of extracted data:")
        print(output_df.head())

        print(f"\nThis '{OUTPUT_PEAK_DATA_FILE}' file can now be used as input for your main ML script.")
        print(
            f"Remember to merge it with your growth parameters (well_width, growth_temp, in_fraction) using the 'PL_Sample' column.")
