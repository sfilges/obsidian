import uuid
import os
import time
from pathlib import Path
import yaml
from datetime import datetime
try:
    from obsidian.config import TEMPLATE_PATH
except ImportError:
    from config import TEMPLATE_PATH

# --- HELPER FUNCTIONS ---

def generate_frontmatter(doc, source_path: str, type: str = "general", status: str = "draft", tags: list = []):
    """
    Creates Obsidian-friendly YAML frontmatter.
    """
    # Attempt to extract title, defaulting to filename if extraction fails
    title = doc.name if doc.name else Path(source_path).stem
    
    # Current date for "Added" field
    date_added = time.strftime("%Y-%m-%d")
    
    frontmatter = "---\n"
    frontmatter += f"id: {uuid.uuid4()}\n"
    frontmatter += f"title: \"{title}\"\n"
    frontmatter += f"type: {type}\n"
    frontmatter += f"status: {status}\n"
    frontmatter += f"added: {date_added}\n"
    frontmatter += f"tags: {tags}\n"
    frontmatter += f"source: {source_path}\n"
    frontmatter += "---\n\n"
    
    return frontmatter, title


def get_frontmatter(doc, source_path):
    """
    Loads the YAML template and fills in the placeholders.
    """
    # Prepare data for placeholders
    title = doc.name if doc.name else Path(source_path).stem
    date_added = time.strftime("%Y-%m-%d")
    clean_source = str(source_path)

    # Define the default fallback in case template is missing
    default_template = "---\ntitle: \"{title}\"\nadded: {date}\n---\n\n"

    try:
        if TEMPLATE_PATH.exists():
            with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                template_content = f.read()
        else:
            print(f"⚠️ Warning: Template not found at {TEMPLATE_PATH}. Using default.")
            template_content = default_template

        # Fill placeholders
        # We use .format() so your yaml can contain {title}, {date}, {source}
        formatted_frontmatter = template_content.format(
            title=title, 
            date=date_added, 
            source=clean_source
        )
        return formatted_frontmatter, title

    except KeyError as e:
        print(f"❌ Template Error: Your YAML contains a placeholder {e} that the script doesn't provide.")
        return default_template.format(title=title, date=date_added), title
    except Exception as e:
        print(f"❌ Error loading template: {e}")
        return default_template.format(title=title, date=date_added), title


def parse_frontmatter(file_content: str):
    """(Same as previous script)"""
    if file_content.startswith("---"):
        try:
            parts = file_content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                content = parts[2].strip()
                return frontmatter, content
        except yaml.YAMLError:
            pass
    return {}, file_content


def get_file_metadata(filepath: str, frontmatter: dict):
    """(Same as previous script)"""
    stats = os.stat(filepath)
    filename = os.path.basename(filepath)
    return {
        "title": frontmatter.get("title", filename.replace(".md", "")),
        "note_type": frontmatter.get("type", "general"),
        "status": frontmatter.get("status", "active"),
        "created": str(frontmatter.get("created", datetime.fromtimestamp(stats.st_ctime).date())),
        "tags": ",".join(frontmatter.get("tags", [])),
        "last_modified": stats.st_mtime
    }