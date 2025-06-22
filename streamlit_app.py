import streamlit as st
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict
import io
import zipfile

# Page configuration
st.set_page_config(
    page_title="SKU-wise PDF Splitter",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stFileUploader > div > div > div > div {
        text-align: center;
    }
    .success-message {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #e7f3ff;
        border: 1px solid #b8daff;
        color: #004085;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📦 SKU-wise PDF Splitter")
st.markdown("Upload your Meesho order labels PDF and get individual PDFs organized by SKU")

# Instructions
with st.expander("ℹ️ How to use this tool"):
    st.markdown("""
    1. **Upload PDF**: Click the upload button and select your Meesho order labels PDF
    2. **Processing**: The app will automatically detect SKUs on each page
    3. **Download**: Get a ZIP file containing separate PDFs for each SKU
    
    **Note**: Pages without identifiable SKUs will be grouped in an "unidentified_pages.pdf" file.
    """)

# File uploader
uploaded_pdf = st.file_uploader(
    "Choose your PDF file",
    type=["pdf"],
    help="Upload the Meesho order labels PDF file you want to split by SKU"
)

if uploaded_pdf is not None:
    # Show file details
    st.markdown(f"**File uploaded:** {uploaded_pdf.name}")
    st.markdown(f"**File size:** {uploaded_pdf.size / 1024:.1f} KB")
    
    # Processing section
    with st.spinner("🔄 Processing PDF and extracting SKUs..."):
        try:
            # SKU bounding box coordinates (adjust if needed)
            sku_bbox = (17, 327, 73, 342)  # (x0, top, x1, bottom)
            
            # Initialize data structures
            sku_to_pages = defaultdict(list)
            unidentified_pages = []
            last_valid_sku = None
            
            # Read PDF bytes once
            pdf_bytes = uploaded_pdf.read()
            pdf_stream = io.BytesIO(pdf_bytes)
            
            # Extract SKUs from each page with optimizations
            with pdfplumber.open(pdf_stream) as pdf:
                total_pages = len(pdf.pages)
                st.info(f"📄 Processing {total_pages} pages...")
                
                # Create a progress bar for better UX
                progress_bar = st.progress(0)
                
                for i, page in enumerate(pdf.pages):
                    # Update progress
                    progress_bar.progress((i + 1) / total_pages)
                    
                    # Crop to SKU area first to reduce processing
                    sku_area = page.crop(sku_bbox)
                    
                    # Extract text only from the cropped area
                    sku_text = sku_area.extract_text()
                    
                    if sku_text and sku_text.strip():
                        # Split by whitespace and take first valid token
                        tokens = sku_text.strip().split()
                        if tokens and len(tokens[0]) >= 4:
                            sku = tokens[0]
                            sku_to_pages[sku].append(i)
                            last_valid_sku = sku
                        else:
                            # Fallback to last valid SKU
                            if last_valid_sku:
                                sku_to_pages[last_valid_sku].append(i)
                            else:
                                unidentified_pages.append(i)
                    else:
                        # No text found, use last valid SKU or mark unidentified
                        if last_valid_sku:
                            sku_to_pages[last_valid_sku].append(i)
                        else:
                            unidentified_pages.append(i)
                
                # Clear progress bar
                progress_bar.empty()
            
            # Show processing results
            st.success("✅ SKU extraction completed!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("SKUs Found", len(sku_to_pages))
            with col2:
                st.metric("Unidentified Pages", len(unidentified_pages))
            
            # Create ZIP file with split PDFs
            st.subheader("📥 Download Split PDFs")
            
            pdf_stream.seek(0)  # Reset stream position
            reader = PdfReader(pdf_stream)
            output_zip = io.BytesIO()
            
            # Create progress bar for PDF generation
            pdf_progress = st.progress(0)
            total_operations = len(sku_to_pages) + (1 if unidentified_pages else 0)
            current_operation = 0
            
            with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as zipf:
                # Create PDF for each SKU
                for sku, page_indices in sku_to_pages.items():
                    writer = PdfWriter()
                    
                    # Add pages in batch
                    for idx in page_indices:
                        writer.add_page(reader.pages[idx])
                    
                    buffer = io.BytesIO()
                    writer.write(buffer)
                    zipf.writestr(f"{sku}.pdf", buffer.getvalue())
                    
                    current_operation += 1
                    pdf_progress.progress(current_operation / total_operations)
                
                # Create PDF for unidentified pages if any
                if unidentified_pages:
                    writer = PdfWriter()
                    for idx in unidentified_pages:
                        writer.add_page(reader.pages[idx])
                    
                    buffer = io.BytesIO()
                    writer.write(buffer)
                    zipf.writestr("unidentified_pages.pdf", buffer.getvalue())
                    
                    current_operation += 1
                    pdf_progress.progress(current_operation / total_operations)
            
            # Clear progress bar
            pdf_progress.empty()
            
            # Download button
            st.download_button(
                label="📦 Download All PDFs as ZIP",
                data=output_zip.getvalue(),
                file_name=f"sku_split_{uploaded_pdf.name.replace('.pdf', '')}.zip",
                mime="application/zip",
                help="Download a ZIP file containing separate PDFs for each SKU"
            )
            
            st.markdown("---")
            st.markdown("🎉 **Success!** Your PDFs have been split by SKU and are ready for download.")
            
        except Exception as e:
            st.error(f"❌ An error occurred while processing the PDF: {str(e)}")
            st.markdown("Please check that:")
            st.markdown("- The uploaded file is a valid PDF")
            st.markdown("- The PDF contains the expected SKU format")
            st.markdown("- The file is not corrupted or password-protected")

else:
    st.info("👆 Upload your PDF file to begin splitting by SKU")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit | Upload your PDF to begin")