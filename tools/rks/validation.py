"""Check that the final office save retained editable literals and pictures."""
from collections import Counter
import re

from docx import Document
from docx.text.paragraph import Paragraph


def validate_docx(extracted, path):
    expected = []
    images = 0
    for page in extracted["pages"]:
        for element in page["elements"]:
            if element["kind"] in {"paragraph", "heading"}:
                expected.append(element["text"])
            elif element["kind"] == "table" and element["editable"]:
                expected.extend(str(cell or "") for row in element["rows"] for cell in row)
            else:
                images += 1
    document = Document(path)
    if extracted.get("cover_logo"):
        images += 1
    actual = "\n".join(Paragraph(p, document).text for p in document.element.xpath('.//w:p'))
    missing = Counter(re.findall(r"\S+", "\n".join(expected))) - Counter(re.findall(r"\S+", actual))
    return {"missing_literal_tokens": sum(missing.values()), "expected_images": images,
            "actual_images": len(document.inline_shapes),
            "passed": not missing and len(document.inline_shapes) == images}
