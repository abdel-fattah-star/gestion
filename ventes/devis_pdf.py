from io import BytesIO
from django.http import HttpResponse
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, PageBreak, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import qrcode
from core.utils import get_societe
from core.report_styles import STYLE_LIBELLE

def generer_devis_pdf(devis):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=10,
        bottomMargin=30,
    )

    elements = []
    styles = getSampleStyleSheet()

    # ======================
    # QR CODE
    # ======================

    qr_data = f"""
    Devis: {devis.numero}
    Client: {devis.client.nom}
    Date: {devis.date.strftime('%d/%m/%Y')}
    Total Ttc: {devis.total_ttc}
    """

    qr = qrcode.make(qr_data)

    qr_buffer = BytesIO()
    qr.save(qr_buffer)
    qr_buffer.seek(0)

    qr_image = Image(qr_buffer, 3*cm, 3*cm)

    # ======================
    # ENTETE SOCIETE
    # ======================

    societe = get_societe()

    societe_info = [
        [Paragraph(societe.nom, styles["Heading2"])],
        [Paragraph(
            f"Adresse : {societe.adresse} - {societe.ville} - {societe.pays}",
            styles["Normal"]
        )],
        [Paragraph(
            f"MF      : {societe.matricule_fiscal}",
            styles["Normal"]
        )],
        [Paragraph(
            f"Tel     : {societe.telephone}",
            styles["Normal"]
        )],
        [Paragraph(
            f"Email   : {societe.email}",
            styles["Normal"]
        )],
    ]

    elements.append(Spacer(1,20))
    societe_table = Table(societe_info)

    header_table = Table(
        [[societe_table, qr_image]],
        colWidths=[13*cm, 3*cm]
    )

    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))

    elements.append(header_table)
    elements.append(Spacer(0,0))

    elements.append(Paragraph(f"<b>DEVIS N° {devis.numero}</b>", styles["Heading2"]))
    elements.append(Paragraph(f"Date : {devis.date.strftime('%d/%m/%Y')}", styles["Normal"]))

    elements.append(Spacer(1, 20))

    # ======================
    # CLIENT
    # ======================

    client_data = [
        ["Client", devis.client.nom],
        ["Matricule Fiscal", devis.mf_client or ""],
        ["Adresse", devis.adresse_client or ""],
        ["Téléphone", devis.telephone_client or ""],
        ["Email", devis.email_client or ""],
    ]

    client_table = Table(client_data, colWidths=[5*cm, 13*cm])

    client_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))

    elements.append(client_table)
    elements.append(Spacer(1, 25))

    # ======================
    # LIGNES DEVIS
    # ======================

    lignes = list(devis.lignes.all())

    lignes_par_page = 16
    total_lignes = len(lignes)

    pages = (total_lignes // lignes_par_page) + 1

    index = 0

    for page in range(pages):

        data = [["Produit", "Qté", "Prix HT", "Rem %", "TVA %", "Total TTC"]]

        for i in range(lignes_par_page):

            if index < total_lignes:

                ligne = lignes[index]

                montant_ht = ligne.quantite * ligne.prix_ht
                montant_rem = montant_ht * (ligne.taux_rem or 0) / 100
                base_tva = montant_ht - montant_rem
                montant_tva = base_tva * (ligne.taux_tva or 0) / 100
                montant_ttc = base_tva + montant_tva

                data.append([
                    Paragraph(str(ligne.produit), STYLE_LIBELLE),
                    f"{ligne.quantite}",
                    f"{ligne.prix_ht:.3f}",
                    "" if (ligne.taux_rem or 0) == 0 else f"{ligne.taux_rem}",
                    f"{ligne.taux_tva}",
                    f"{montant_ttc:.3f}",
                ])

                index += 1

            else:
                data.append(["", "", "", "", "", ""])

        table = Table(
            data,
            colWidths=[7*cm, 2*cm, 3*cm, 2*cm, 2*cm, 3*cm]
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86C1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))

        elements.append(table)

        if page < pages - 1:
            elements.append(PageBreak())

    elements.append(Spacer(1, 20))

    # ======================
    # TOTAUX
    # ======================

    totaux = devis.calculer_totaux()

    total_data = [
        ["Total HT", f"{totaux['total_ht']:.3f} TND"],
        ["Total Remise", f"{totaux['total_rem']:.3f} TND"],
        ["Base TVA", f"{totaux['base_tva']:.3f} TND"],
        ["Total TVA", f"{totaux['total_tva']:.3f} TND"],
        ["Total TTC", f"{totaux['total_ttc']:.3f} TND"],
    ]

    total_table = Table(total_data, colWidths=[13*cm, 6*cm])

    total_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("BACKGROUND", (0, 4), (-1, 4), colors.lightgrey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))

    elements.append(total_table)
    elements.append(Spacer(1, 20))

    # ======================
    # COMMENTAIRE
    # ======================

    comment_data = [
        ["Pour commander appeller la societé"],
    ]

    comment_table = Table(comment_data, colWidths=[18*cm])

    comment_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    elements.append(comment_table)
    elements.append(Spacer(1, 25))

    # ======================
    # GENERATION PDF
    # ======================

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="devis_{devis.numero}.pdf"'
    response.write(pdf)

    return response