
from pathlib import Path
from html import escape
from time import monotonic

import markdown
from tqdm import tqdm
from weasyprint import HTML


# =========================
# CONFIGURATION
# =========================

INPUT_DIR = Path("notes")
OUTPUT_FILE = Path("output.pdf")

# "name" = alphabetical order
# "time" = modification time
SORT_MODE = "name"

MARKDOWN_EXTENSIONS = ["extra", "sane_lists"]


# =========================
# STEP 1: FIND MARKDOWN FILES
# =========================

def get_markdown_files(directory: Path) -> list[Path]:
    """Find and sort Markdown files recursively."""

    if not directory.is_dir():
        raise FileNotFoundError(
            f"Input directory does not exist: {directory.resolve()}"
        )

    files = list(directory.rglob("*.md"))

    if SORT_MODE == "time":
        files.sort(key=lambda file: file.stat().st_mtime)
    else:
        files.sort(key=lambda file: str(file).casefold())

    return files


# =========================
# STEP 2: CONVERT MARKDOWN
# =========================

def merge_markdown(files: list[Path]) -> str:
    """Convert Markdown files to HTML with progress reporting."""

    html_parts = []
    failed = 0
    started = monotonic()

    with tqdm(
        total=len(files),
        desc="Converting Markdown",
        unit="file",
        dynamic_ncols=True,
        smoothing=0.15,
    ) as progress:

        for file in files:
            try:
                text = file.read_text(encoding="utf-8")

                converted = markdown.markdown(
                    text,
                    extensions=MARKDOWN_EXTENSIONS,
                )

                title = escape(file.stem)

                html_parts.append(
                    f'<section class="note">'
                    f"<h1>{title}</h1>\n"
                    f"{converted}\n"
                    f"</section>"
                )

            except (OSError, UnicodeError, ValueError) as exc:
                failed += 1
                tqdm.write(f"ERROR: {file}: {exc}")

            finally:
                progress.update(1)

                elapsed = monotonic() - started
                processed = progress.n
                rate = processed / elapsed if elapsed > 0 else 0

                progress.set_postfix(
                    successful=len(html_parts),
                    errors=failed,
                    rate=f"{rate:.1f} files/s",
                )

    print(
        f"\nMarkdown conversion finished: "
        f"{len(html_parts)} successful, {failed} failed."
    )

    return "\n<hr class=\"note-separator\">\n".join(html_parts)


# =========================
# STEP 3: BUILD HTML DOCUMENT
# =========================

def build_html_document(body: str) -> str:
    """Wrap converted content in a complete HTML document."""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        @page {{
            margin: 18mm;
        }}

        body {{
            font-family: sans-serif;
            line-height: 1.6;
        }}

        h1 {{
            border-bottom: 1px solid #ccc;
            page-break-after: avoid;
        }}

        h2, h3, h4 {{
            page-break-after: avoid;
        }}

        pre, blockquote, table {{
            page-break-inside: avoid;
        }}

        img {{
            max-width: 100%;
            height: auto;
        }}

        .note {{
            overflow-wrap: break-word;
        }}

        .note-separator {{
            margin: 2em 0;
            border: 0;
            border-top: 1px solid #bbb;
        }}
    </style>
</head>

<body>
{body}
</body>
</html>
"""


# =========================
# STEP 4: GENERATE PDF
# =========================

def html_to_pdf(html_content: str, output: Path) -> None:
    """Render the HTML document to a PDF file."""

    output.parent.mkdir(parents=True, exist_ok=True)

    HTML(
        string=html_content,
        base_url=str(Path.cwd().resolve()),
    ).write_pdf(str(output))


# =========================
# STEP 5: MAIN PROGRAM
# =========================

def main() -> None:
    total_started = monotonic()

    try:
        md_files = get_markdown_files(INPUT_DIR)

    except OSError as exc:
        print(f"Input error: {exc}")
        return

    if not md_files:
        print(f"No Markdown files found in: {INPUT_DIR.resolve()}")
        return

    print(f"Found {len(md_files):,} Markdown files.")

    # Convert Markdown and display progress.
    merged_html = merge_markdown(md_files)

    if not merged_html.strip():
        print("No content could be converted. PDF was not created.")
        return

    # Build the complete HTML document.
    full_html = build_html_document(merged_html)

    # Render PDF.
    print("\nGenerating PDF...")
    print(
        "Note: WeasyPrint does not provide a reliable "
        "percentage indicator for PDF rendering."
    )

    pdf_started = monotonic()

    try:
        html_to_pdf(full_html, OUTPUT_FILE)

    except Exception as exc:
        print(f"PDF generation failed: {exc}")
        raise

    pdf_elapsed = monotonic() - pdf_started
    total_elapsed = monotonic() - total_started

    print("\nPDF created successfully!")
    print(f"Output: {OUTPUT_FILE.resolve()}")
    print(f"PDF rendering time: {pdf_elapsed:.1f} seconds")
    print(f"Total execution time: {total_elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
