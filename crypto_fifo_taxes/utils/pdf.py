from io import BytesIO
from typing import Any

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa  # type: ignore

from crypto_fifo_taxes.exceptions import PdfException


def render_to_pdf(template: str, context: dict[str, Any]) -> HttpResponse:
    """Render passed template to a pdf file"""
    html = get_template(template).render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if pdf.err:
        raise PdfException(pdf.err)
    return HttpResponse(result.getvalue(), content_type="application/pdf")
