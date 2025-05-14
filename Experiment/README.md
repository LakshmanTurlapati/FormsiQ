# PDF Form Field Extraction and Filling

This project contains scripts for extracting fillable fields from a PDF form and filling them with provided variables.

## Requirements

- Python 3.6+
- PyMuPDF (also known as fitz)

Install the required packages:

```bash
pip install pymupdf
```

## Files

- `extract_pdf_fields.py`: Script to extract all fillable fields from a PDF
- `fill_pdf_fields.py`: Script to fill a PDF with provided variables that have confidence above a threshold
- `uniform_residential_loan_application.pdf`: Sample PDF form
- `output/`: Directory containing output files
  - `filled_uniform_residential_loan_application.pdf`: Filled PDF form
  - `fill_report.json`: Detailed report of the filling process
  - `processing_summary.txt`: Summary of the process

## Usage

### 1. Extract Fillable Fields

To extract all fillable fields from the PDF:

```bash
python extract_pdf_fields.py
```

This will create:
- `pdf_fields.txt`: Text listing of all fillable fields
- `pdf_fields.json`: JSON data of all fillable fields

### 2. Fill PDF with Variables

To fill the PDF with variables:

```bash
python fill_pdf_fields.py
```

The script uses the variables defined in the `variables_text` variable in the script. You can modify this variable or update the script to read from a file.

Only variables with confidence levels above the threshold (default 80%) will be filled.

## Input Variable Format

The input variables should be in the following tab-separated format:

```
Field Name    Value    Confidence%
```

Example:
```
Borrower First Name    Brenda    100%
Social Security Number    987-65-6789    80%
```

## Custom Field Mapping

The script uses a mapping dictionary to match variable names to PDF field names. You can customize this mapping in the `map_variable_to_pdf_field` function in `fill_pdf_fields.py`.

## Value Formatting

The script automatically formats values based on the field type:
- Dates (YYYY-MM-DD) are formatted as MM/DD/YYYY
- SSNs (XXX-XX-XXXX) have hyphens removed
- Currency values have $ and commas removed

## Troubleshooting

If fields are not being filled correctly:
1. Check the field mapping in the script
2. Verify that the confidence level is above the threshold
3. Look at the detailed report in `output/fill_report.json`
4. Check if the field exists in the PDF using the output from `extract_pdf_fields.py` 