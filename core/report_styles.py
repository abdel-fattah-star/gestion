from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

styles = getSampleStyleSheet()

STYLE_LIBELLE = ParagraphStyle(
    "STYLE_LIBELLE",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=10,
    wordWrap="CJK",
)

STYLE_LIBELLE_BOLD = ParagraphStyle(
    "STYLE_LIBELLE_BOLD",
    parent=STYLE_LIBELLE,
    fontName="Helvetica-Bold",
)