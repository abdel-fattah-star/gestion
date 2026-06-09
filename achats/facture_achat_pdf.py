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
def generer_facture_achat_pdf(facture):

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
    Facture Achat: {facture.numero}
    Fournisseur: {facture.fournisseur.nom}
    Date: {facture.date.strftime('%d/%m/%Y')}
    Total TTC: {facture.total_ttc}
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
        colWidths=[16*cm, 4*cm]
    )

    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))

    elements.append(header_table)

    elements.append(Paragraph(f"<b>FACTURE ACHAT N° {facture.numero}</b>", styles["Heading2"]))
    elements.append(Paragraph(f"Date : {facture.date.strftime('%d/%m/%Y')}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    # ======================
    # FOURNISSEUR
    # ======================

    fournisseur_data = [
        ["Fournisseur", facture.fournisseur.nom],
        ["Matricule Fiscal", facture.fournisseur.matricule_fiscal or ""],
        ["Adresse", facture.fournisseur.adresse or ""],
        ["Téléphone", facture.fournisseur.telephone or ""],
        ["Email", facture.fournisseur.email or ""],
    ]

    fournisseur_table = Table(fournisseur_data, colWidths=[5*cm, 13*cm])

    fournisseur_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))

    elements.append(fournisseur_table)
    elements.append(Spacer(1, 25))

    # ======================
    # LIGNES FACTURE
    # ======================

    lignes = list(facture.lignes.all())

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

    totaux = facture.calculer_totaux()

    total_data = [
        ["Total HT", f"{totaux['total_ht']:.3f} TND"],
        ["Total Remise", f"{totaux['total_rem']:.3f} TND"],
        ["Base TVA", f"{totaux['base_tva']:.3f} TND"],
        ["Total TVA", f"{totaux['total_tva']:.3f} TND"],
        ["Timbre.fiscale", f"{1:.3f} TND"],
        ["Total TTC", f"{totaux['total_ttc']:.3f} TND"],
    ]

    total_table = Table(total_data, colWidths=[6*cm, 13*cm])

    total_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("BACKGROUND", (0, 5), (-1, 5), colors.lightgrey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))

    elements.append(total_table)

    elements.append(Spacer(1, 20))


    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="facture_achat_{facture.numero}.pdf"'
    response.write(pdf)

    return response