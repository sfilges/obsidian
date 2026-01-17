"""
Document conversion module for obsidian package.

Provides functions to convert PDFs to Obsidian-compatible markdown using Docling.
"""

import logging
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableStructureOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from obsidian.config import EXTRACTOR_BACKEND
from obsidian.extract import extract_metadata
from obsidian.utils import generate_frontmatter

logger = logging.getLogger(__name__)


def get_converter() -> DocumentConverter:
    """
    Configures Docling with specific options for research papers:
    - Enables detailed table structure recognition
    - Enables OCR (useful for older scanned papers)
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(do_cell_matching=True)

    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)})


def process_paper(pdf_path: Path, vault_path: Path, extract: bool = False):
    """
    Process a single PDF and convert it to Obsidian markdown.

    Args:
        pdf_path: Path to the PDF file
        vault_path: Path to save the converted markdown
        extract: If True, run LLM metadata extraction and set status to "active"
    """
    logger.info("📄 Processing: %s...", pdf_path)

    converter = get_converter()

    try:
        # 1. Convert the PDF
        result = converter.convert(pdf_path)
        doc = result.document

        # 2. Export to Markdown
        # Docling does a great job of converting tables to Markdown syntax automatically
        markdown_content = doc.export_to_markdown()

        # 3. Extract metadata using LLM (if requested and configured)
        authors = []
        summary = ""
        tags = ["paper", "research-article"]
        status = "pending"  # Default to pending

        if extract and EXTRACTOR_BACKEND.lower() != "none":
            logger.info("Extracting metadata using %s...", EXTRACTOR_BACKEND)
            metadata = extract_metadata(markdown_content)
            if metadata.authors:
                authors = metadata.authors
            if metadata.summary:
                summary = metadata.summary
            if metadata.tags:
                tags = list(set(tags + metadata.tags))  # Merge with default tags
            status = "active"  # Set to active after successful extraction
        elif extract:
            logger.warning("Extraction requested but no backend configured (EXTRACTOR_BACKEND=%s)", EXTRACTOR_BACKEND)

        # 4. Prepare Frontmatter
        frontmatter, title = generate_frontmatter(
            doc,
            str(pdf_path),
            note_type="paper",
            status=status,
            tags=tags,
            authors=authors,
            summary=summary,
        )

        # 5. Construct final file content
        final_content = frontmatter + markdown_content

        # 6. Save to Obsidian
        save_path = Path(vault_path)
        save_path.mkdir(parents=True, exist_ok=True)

        # Clean filename (remove illegal characters)
        safe_filename = "".join([c for c in title if c.isalpha() or c.isdigit() or c in " ._-"]).strip()
        output_file = save_path / f"{safe_filename}.md"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_content)

        logger.info("✅ Success! Saved to: %s", output_file)

    except Exception as e:
        logger.error("❌ Error processing %s: %s", pdf_path, e)


def batch_convert_pdfs(pdf_paths: Path, vault_path: Path, extract: bool = False):
    """
    Convert all PDFs in a directory to markdown.

    Args:
        input_dir: Directory containing PDFs (searched recursively)
        vault_path: Path to save converted markdown files
        extract: If True, run LLM metadata extraction and set status to "active"
    """
    pdf_paths = Path(input_dir).glob("**/*.pdf")
    for pdf_path in pdf_paths:
        process_paper(pdf_path, vault_path, extract=extract)
