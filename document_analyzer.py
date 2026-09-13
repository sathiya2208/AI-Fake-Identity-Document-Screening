from PIL import Image
import pytesseract


def extract_text(image):
    """Extract text from the uploaded identity document."""
    text = pytesseract.image_to_string(image)
    return text.strip()


def analyze_document(image):
    """Perform basic document analysis."""
    text = extract_text(image)

    result = {
        "text": text,
        "text_found": bool(text),
        "text_length": len(text)
    }

    if not text:
        result["status"] = "LOW QUALITY / UNREADABLE"
    else:
        result["status"] = "TEXT DETECTED"

    return result
