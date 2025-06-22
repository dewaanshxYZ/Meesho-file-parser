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
            
            # Read PDF bytes
            pdf_bytes = uploaded_pdf.read()
            pdf_stream = io.BytesIO(pdf_bytes)
            
            # Extract SKUs from each page
            with pdfplumber.open(pdf_stream) as pdf:
                total_pages = len(pdf.pages)
                st.info(f"📄 Processing {total_pages} pages...")
                
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
                        # If no SKU found, append to last valid SKU or mark as unidentified
                        if last_valid_sku:
                            sku_to_pages[last_valid_sku].append(i)
                        else:
                            unidentified_pages.append(i)
            
            # Show processing results
            st.success("✅ SKU extraction completed!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("SKUs Found", len(sku_to_pages))
            with col2:
                st.metric("Unidentified Pages", len(unidentified_pages))
            
            # Show SKU breakdown
            if sku_to_pages:
                st.subheader("📊 SKU Breakdown")
                for sku, pages in sku_to_pages.items():
                    page_numbers = [p + 1 for p in pages]  # Convert to 1-based indexing
                    st.write(f"**{sku}**: {len(pages)} pages ({', '.join(map(str, page_numbers))})")
            
            # Create ZIP file with split PDFs
            st.subheader("📥 Download Split PDFs")
            
            pdf_stream.seek(0)  # Reset stream position
            reader = PdfReader(pdf_stream)
            output_zip = io.BytesIO()
            
            with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Create PDF for each SKU
                for sku, page_indices in sku_to_pages.items():
                    writer = PdfWriter()
                    for idx in page_indices:
                        writer.add_page(reader.pages[idx])
                    
                    buffer = io.BytesIO()
                    writer.write(buffer)
                    zipf.writestr(f"{sku}.pdf", buffer.getvalue())
                
                # Create PDF for unidentified pages if any
                if unidentified_pages:
                    writer = PdfWriter()
                    for idx in unidentified_pages:
                        writer.add_page(reader.pages[idx])
                    
                    buffer = io.BytesIO()
                    writer.write(buffer)
                    zipf.writestr("unidentified_pages.pdf", buffer.getvalue())
            
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
    # Landing page content
    st.markdown("---")
    st.markdown("### 🚀 Ready to get started?")
    st.markdown("Upload your Meesho order labels PDF above to automatically split it by SKU codes.")
    
    # Feature highlights
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🎯 Accurate**")
        st.markdown("Precisely identifies SKUs using coordinate-based extraction")
    
    with col2:
        st.markdown("**⚡ Fast**")
        st.markdown("Processes large PDFs quickly and efficiently")
    
    with col3:
        st.markdown("**📦 Organized**")
        st.markdown("Downloads as a convenient ZIP file with separate PDFs")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit | Upload your PDF to begin")