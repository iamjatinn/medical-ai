import pymupdf


def extract_text_from_pdf(pdf_path):

    try:
        document = pymupdf.open(str(pdf_path))
    except Exception as error:
        raise ValueError("The uploaded file is not a readable PDF.") from error

    try:
        text = "".join(page.get_text() for page in document)
    finally:
        document.close()

    if not text.strip():
        raise ValueError(
            "No text could be read from this PDF. It may be a scanned image "
            "(OCR is not supported yet)."
        )

    return text
