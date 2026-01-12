"""
Document conversion module for obsidian package.

Provides functions to convert PDFs to Obsidian-compatible markdown using Docling.
"""

from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions

from obsidian.utils import generate_frontmatter


def get_converter() -> DocumentConverter:
    """
    Configures Docling with specific options for research papers:
    - Enables detailed table structure recognition
    - Enables OCR (useful for older scanned papers)
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )


def process_paper(pdf_path: Path, vault_path: Path):
    """
    Process a single PDF and convert it to Obsidian markdown.
    
    Args:
        pdf_path: Path to the PDF file
        vault_path: Path to save the converted markdown
    """
    print(f"📄 Processing: {pdf_path}...")
    
    converter = get_converter()
    
    try:
        # 1. Convert the PDF
        result = converter.convert(pdf_path)
        doc = result.document
        
        # 2. Export to Markdown
        # Docling does a great job of converting tables to Markdown syntax automatically
        markdown_content = doc.export_to_markdown()
        
        # 3. Prepare Frontmatter
        frontmatter, title = generate_frontmatter(
            doc,
            pdf_path,
            type="paper",
            status="active",
            tags=["paper", "research-article"]
        )
        
        # 4. Construct final file content
        final_content = frontmatter + markdown_content
        
        # 5. Save to Obsidian
        save_path = Path(vault_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Clean filename (remove illegal characters)
        safe_filename = "".join([c for c in title if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
        output_file = save_path / f"{safe_filename}.md"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        print(f"✅ Success! Saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error processing {pdf_path}: {e}")


def batch_convert_pdfs(pdf_paths: Path, vault_path: Path):
    """
    Convert all PDFs in a directory to markdown.
    
    Args:
        pdf_paths: Directory containing PDFs (searched recursively)
        vault_path: Path to save converted markdown files
    """
    pdf_paths = Path(pdf_paths).glob("**/*.pdf")
    for pdf_path in pdf_paths:
        process_paper(pdf_path, vault_path)