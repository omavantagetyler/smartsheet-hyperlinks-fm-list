import os
import sys
import smartsheet

# Load Secrets from Environment
API_TOKEN = os.environ.get("SMARTSHEET_ACCESS_KEY")
SHEET_ID_STR = os.environ.get("SMARTSHEET_SHEET_ID")

if not API_TOKEN or not SHEET_ID_STR:
    print("Error: Missing required environment variables.")
    sys.exit(1)

SHEET_ID = int(SHEET_ID_STR)
BASE_URL = "https://am-desktop.corrigopro.com/ServiceChat/Chat/ReRoute?Filter="

# Initialize Smartsheet Client
sm = smartsheet.Smartsheet(API_TOKEN)
sm.errors_as_exceptions(True)

def run():
    print(f"Fetching sheet {SHEET_ID}...")
    sheet = sm.Sheets.get_sheet(SHEET_ID)

    # Map column headers to IDs
    col_map = {col.title: col.id for col in sheet.columns}

    # Column names
    WO_COL_NAME = "Work Order #"
    OMA_COL_NAME = "OMA CX#"

    if WO_COL_NAME not in col_map or OMA_COL_NAME not in col_map:
        print(f"Error: Could not find required columns on sheet. Available: {list(col_map.keys())}")
        sys.exit(1)

    wo_col_id = col_map[WO_COL_NAME]
    oma_col_id = col_map[OMA_COL_NAME]

    rows_to_update = []

    for row in sheet.rows:
        oma_val = None
        wo_val = None
        wo_cell_current_hyperlink = None

        # Parse cells in row
        for cell in row.cells:
            if cell.column_id == oma_col_id:
                oma_val = cell.value
            elif cell.column_id == wo_col_id:
                wo_val = cell.value
                # Check if it already has a hyperlink
                if cell.hyperlink and cell.hyperlink.url:
                    wo_cell_current_hyperlink = cell.hyperlink.url

        # Check Condition 1: OMA CX# is NOT blank (not None and not empty/whitespace string)
        oma_has_value = oma_val is not None and str(oma_val).strip() != ""

        # Check Condition 2: Work Order # HAS a value to append
        wo_has_value = wo_val is not None and str(wo_val).strip() != ""

        if oma_has_value and wo_has_value:
            wo_string = str(wo_val).strip()
            target_url = f"{BASE_URL}{wo_string}"

            # Idempotency check: Skip if it already has this exact URL
            if wo_cell_current_hyperlink == target_url:
                continue

            # Construct cell update
            updated_cell = smartsheet.models.Cell({
                'column_id': wo_col_id,
                'value': wo_string,
                'hyperlink': smartsheet.models.Hyperlink({
                    'url': target_url
                })
            })

            updated_row = smartsheet.models.Row({
                'id': row.id,
                'cells': [updated_cell]
            })

            rows_to_update.append(updated_row)

    # Batch updates (Smartsheet cap is 500 rows per request)
    total_to_update = len(rows_to_update)
    if total_to_update > 0:
        print(f"Found {total_to_update} rows needing hyperlink updates.")
        chunk_size = 500
        for i in range(0, total_to_update, chunk_size):
            chunk = rows_to_update[i:i + chunk_size]
            sm.Sheets.update_rows(SHEET_ID, chunk)
            print(f"Updated rows {i + 1} to {min(i + chunk_size, total_to_update)}")
        print("Update complete!")
    else:
        print("No rows required updating.")

if __name__ == "__main__":
    run()
