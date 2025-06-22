import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict
from pathlib import Path

# === Setup ===
input_pdf_path = "/Users/dewaanshvijayvargiya/Documents/My Apps/Meesho file parser/Sub_Order_Labels_aa2ff64a-634d-4a34-a3c5-d33d2780ab1a.pdf"
output_dir = Path("split_output_by_sku")
output_dir.mkdir(exist_ok=True)

sku_bbox = (17, 327, 73, 342)  # (x0, top, x1, bottom)

sku_to_pages = defaultdict(list)
unidentified_pages = []

last_valid_sku = None  # Track the last valid SKU

# === Step 1: Extract SKU per page ===
with pdfplumber.open(input_pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        words = page.extract_words()
        sku_candidates = [
            word['text'] for word in words
            if sku_bbox[0] <= word['x0'] <= sku_bbox[2] and
               sku_bbox[1] <= word['top'] <= sku_bbox[3]
        ]
        if sku_candidates and len(sku_candidates[0]) >= 4:
            sku = sku_candidates[0]
            sku_to_pages[sku].append(i)
            last_valid_sku = sku
        else:
            if last_valid_sku:
                sku_to_pages[last_valid_sku].append(i)
                # print(f"🔗 Page {i + 1} appended to previous SKU '{last_valid_sku}' (as extension)")
            else:
                unidentified_pages.append(i)
                # print(f"⚠️ SKU not found on page {i + 1} and no previous valid SKU")

# === Step 2: Split PDFs ===
reader = PdfReader(input_pdf_path)

# Save per-SKU PDFs
for sku, page_indices in sku_to_pages.items():
    writer = PdfWriter()
    for idx in page_indices:
        writer.add_page(reader.pages[idx])
    out_path = output_dir / f"{sku}.pdf"
    with open(out_path, "wb") as f_out:
        writer.write(f_out)

# Save unidentified pages to a separate file
if unidentified_pages:
    writer = PdfWriter()
    for idx in unidentified_pages:
        writer.add_page(reader.pages[idx])
    with open(output_dir / "unidentified_pages.pdf", "wb") as f_out:
        writer.write(f_out)

print("✅ Done! All SKU-based PDFs generated.")