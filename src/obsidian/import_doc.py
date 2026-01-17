"""
Document import module for obsidian package.

Provides functions to import documents (PDF, DOCX, HTML, etc.)
and convert them to Obsidian-compatible markdown using Docling.
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

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".htm", ".asciidoc", ".md"}


def get_converter() -> DocumentConverter:
    """
    Configures Docling with specific options for research papers (PDF)
    and enables support for other formats (DOCX, PPTX, HTML, etc.).
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(do_cell_matching=True)

    # Configure PDF options explicitly, other formats use defaults
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )


def import_file(source: str | Path, vault_path: Path, extract: bool = False):
    """
    Process a single document (File or URL) and convert it to Obsidian markdown.

    Args:
        source: Path to the local file or URL string
        vault_path: Path to save the converted markdown
        extract: If True, run LLM metadata extraction and set status to "active"
    """
    logger.info("📄 Processing: %s...", source)

    converter = get_converter()

    try:
        # 1. Convert the Document (handling both Path and URL)
        # Docling's convert method accepts Path or URL string
        result = converter.convert(source)
        doc = result.document

        # 2. Export to Markdown
        markdown_content = doc.export_to_markdown()

        # 3. Extract metadata using LLM (if requested and configured)
        authors = []
        summary = ""
        tags = ["imported-doc"]
        status = "pending"  # Default to pending

        # Simple heuristic for tags
        source_str = str(source).lower()
        if source_str.endswith(".pdf"):
            tags.append("document")
        elif source_str.startswith("http"):
            tags.append("web-clip")

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
            str(source),
            note_type="resource",
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
        if not safe_filename:
            safe_filename = "untitled_import"

        output_file = save_path / f"{safe_filename}.md"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_content)

        logger.info("✅ Success! Saved to: %s", output_file)

    except Exception as e:
        logger.error("❌ Error processing %s: %s", source, e)


def bulk_import(input_dir: Path, vault_path: Path, extract: bool = False):
    """
    Convert all supported documents in a directory to markdown.

    Args:
        input_dir: Directory containing documents (searched recursively)
        vault_path: Path to save converted markdown files
        extract: If True, run LLM metadata extraction and set status to "active"
    """
    input_path = Path(input_dir)
    if not input_path.exists():
         logger.error("Input directory %s does not exist", input_dir)
         return

    # Gather all matching files
    files_to_process = []
    for ext in SUPPORTED_EXTENSIONS:
        files_to_process.extend(input_path.rglob(f"*{ext}"))
        files_to_process.extend(input_path.rglob(f"*{ext.upper()}"))

    # Remove duplicates
    files_to_process = sorted(list(set(files_to_process)))

    if not files_to_process:
        logger.warning("No supported files found in %s", input_dir)
        return

    logger.info("Found %d files to import", len(files_to_process))

    for file_path in files_to_process:
        import_file(file_path, vault_path, extract=extract)
