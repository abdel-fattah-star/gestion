from django.http import JsonResponse
from .models import Fournisseur
from django.utils.html import format_html
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now
from .models import Fournisseur
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.platypus import *
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from dateutil import parser
from core.utils import get_societe
from decimal import Decimal
from django.db.models import Sum
from datetime import datetime
from achats.models import BonReception
from reglements.models import ReglementFournisseur
from .models import Fournisseur
from achats.models import AvoirFournisseur
from decimal import Decimal
from achats.models import BonReception, AvoirFournisseur
from reglements.models import ReglementFournisseur
from decimal import Decimal
from decimal import Decimal
from achats.models import BonReception, AvoirFournisseur
from reglements.models import ReglementFournisseur


def fournisseur_info(request, Fournisseur_id):
    fournisseur = Fournisseur.objects.get(id=Fournisseur_id)

    return JsonResponse({
        "mf": Fournisseur.matricule_fiscal,   # ✅ CORRIGÉ ICI
        "adresse": Fournisseur.adresse,
        "telephone": Fournisseur.telephone,
        "email": Fournisseur.email,
    })


def calcul_releve_fournisseur(fournisseur, date_debut=None, date_fin=None):

    bons = BonReception.objects.filter(fournisseur=fournisseur)
    avoirs = AvoirFournisseur.objects.filter(fournisseur=fournisseur)
    reglements = ReglementFournisseur.objects.filter(fournisseur=fournisseur)

    report = Decimal(fournisseur.solde_initial or 0)

    # =========================
    # REPORT AVANT DATE
    # =========================
    if date_debut:

        report_bons = bons.filter(date__lt=date_debut)
        report_avoirs = avoirs.filter(date__lt=date_debut)
        report_regs = reglements.filter(date__lt=date_debut)

        report += (
            sum(Decimal(b.total_ttc or 0) for b in report_bons)
            - sum(Decimal(a.total_ttc or 0) for a in report_avoirs)
            - sum(Decimal(r.montant or 0) for r in report_regs)
        )

        bons = bons.filter(date__gte=date_debut)
        avoirs = avoirs.filter(date__gte=date_debut)
        reglements = reglements.filter(date__gte=date_debut)

    if date_fin:
        bons = bons.filter(date__lte=date_fin)
        avoirs = avoirs.filter(date__lte=date_fin)
        reglements = reglements.filter(date__lte=date_fin)

    # =========================
    # MOUVEMENTS
    # =========================
    mouvements = []

    # ---- BONS RECEPTION
    for b in bons:
        mouvements.append({
            "date": b.date,
            "libelle": f"Bon réception n° {b.numero}",
            "debit": Decimal(b.total_ttc or 0),
            "credit": Decimal(0),
            "lignes": b.lignes.all(),
            "type": "bon"
        })

    # ---- AVOIRS
    for a in avoirs:
        mouvements.append({
            "date": a.date,
            "libelle": f"Avoir n° {a.numero}",
            "debit": Decimal(0),
            "credit": Decimal(a.total_ttc or 0),
            "lignes": a.lignes.all(),
            "type": "avoir"
        })

    # ---- REGLEMENTS REGROUPES PAR DATE
    regs_par_date = {}

    for r in reglements:

        if r.date not in regs_par_date:

            regs_par_date[r.date] = {
                "date": r.date,
                "libelle": "Règlements",
                "debit": Decimal(0),
                "credit": Decimal(0),
                "lignes": [],
                "details_reglement": [],
                "type": "reglement"
            }

        regs_par_date[r.date]["credit"] += Decimal(r.montant or 0)

        regs_par_date[r.date]["details_reglement"].append({
            "mode_paiement": r.mode_paiement,
            "libelle": getattr(r, "libelle", ""),
            "echeance": r.echeance,
            "montant": Decimal(r.montant or 0)
        })

    mouvements.extend(regs_par_date.values())

    mouvements.sort(key=lambda x: x["date"])

    # =========================
    # SOLDE
    # =========================
    lignes = []
    solde = report

    total_debit = Decimal(0)
    total_credit = Decimal(0)

    if date_debut:
        lignes.append({
            "date": date_debut,
            "libelle": "REPORT",
            "debit": Decimal(0),
            "credit": Decimal(0),
            "solde": solde,
            "lignes": []
        })

    for m in mouvements:
        solde += m["debit"] - m["credit"]
        m["solde"] = solde
        lignes.append(m)

        total_debit += m["debit"]
        total_credit += m["credit"]

    return lignes, solde, report, total_debit, total_credit



def releve_fournisseur(request, fournisseur_id):

    try:
        fournisseur = get_object_or_404(Fournisseur, id=fournisseur_id)

        date_debut = request.GET.get("date_debut")
        date_fin = request.GET.get("date_fin")

        lignes, solde, report, total_debit, total_credit = calcul_releve_fournisseur(
            fournisseur, date_debut, date_fin
        )

        return render(request, "fournisseurs/releve_fournisseur.html", {
            "fournisseur": fournisseur,
            "lignes": lignes,
            "solde": solde,
            "report": report,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "now": now()
        })

    except Exception as e:
        return HttpResponse(f"ERREUR RELEVE FOURNISSEUR : {e}")
    


def releve_fournisseur_pdf(request, fournisseur_id):

    fournisseur = get_object_or_404(Fournisseur, id=fournisseur_id)

    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except:
            try:
                return parser.parse(value).date()
            except:
                return None

    date_debut = parse_date(date_debut)
    date_fin = parse_date(date_fin)

    lignes, solde, report, total_debit, total_credit = calcul_releve_fournisseur(
        fournisseur, date_debut, date_fin
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="releve_fournisseur_{fournisseur.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=0*cm)
    elements = []
    styles = getSampleStyleSheet()

    # ===== STYLE PRODUITS =====
    style_produit = ParagraphStyle(
        "style_produit",
        parent=styles["Normal"],
        fontSize=8,
        leftIndent=8,
    )

    # ===== STYLE TITRE =====
    titre_style = ParagraphStyle(
        "titre_style",
        parent=styles["Heading2"],
        alignment=1,
        fontSize=18,
    )

    # SOCIETE
    societe = get_societe()

    societe_info = [
        [Paragraph(f"<b>{societe.nom}</b>", styles["Heading2"])],
        [Paragraph(f"Adresse : {societe.adresse} - {societe.ville} - {societe.pays}", styles["Normal"])],
        [Paragraph(f"MF : {societe.matricule_fiscal}", styles["Normal"])],
        [Paragraph(f"Tel : {societe.telephone}", styles["Normal"])],
        [Paragraph(f"Email : {societe.email}", styles["Normal"])],
    ]

    elements.append(Spacer(1, 15))
    elements.append(Table(societe_info, colWidths=[18*cm]))

    elements.append(Spacer(1, 10))

    # TITRE CENTRE + PLUS GRAND
    elements.append(
        Paragraph("Releve Fournisseur", titre_style)
    )

    elements.append(Spacer(1, 10))

    # HEADER
    elements.append(
        Paragraph(f"<b>Fournisseur :</b> {fournisseur.nom}", styles["Normal"])
    )

    if date_debut and date_fin:
        elements.append(
            Paragraph(
                f"Période: {date_debut.strftime('%d/%m/%Y')} → {date_fin.strftime('%d/%m/%Y')}",
                styles["Normal"]
            )
        )

    elements.append(
        Paragraph(f"Report initial: {report:.3f}", styles["Normal"])
    )

    elements.append(Spacer(1, 10))

    # TABLE
    data = [["Date", "Libellé", "Débit", "Crédit", "Solde"]]

    for m in lignes:

        data.append([
            m["date"].strftime("%d/%m/%Y"),
            m["libelle"],
            f"{Decimal(m.get('debit',0)):.3f}",
            f"{Decimal(m.get('credit',0)):.3f}",
            f"{Decimal(m.get('solde',0)):.3f}",
        ])

        # =========================
        # DETAILS BONS RECEPTION
        # =========================
        if m.get("type") == "bon":

            for l in m.get("lignes", []):

                data.append([
                    "",
                    Paragraph(
                        f"• {l.quantite} x {l.produit}",
                        style_produit
                    ),
                    "",
                    "",
                    ""
                ])

        # =========================
        # DETAILS AVOIRS -> CREDIT
        # =========================
        elif m.get("type") == "avoir":

            for l in m.get("lignes", []):

                data.append([
                    "",
                    Paragraph(
                        f"• {l.quantite} x {l.produit}",
                        style_produit
                    ),
                    "",
                    "",
                    ""
                ])

        # =========================
        # DETAILS REGLEMENTS
        # =========================
        elif m.get("type") == "reglement":

            for d in m.get("details_reglement", []):

                echeance = (
                    d["echeance"].strftime("%d/%m/%Y")
                    if d.get("echeance")
                    else ""
                )

                txt = (
                    f"{d['montant']:.3f} TND — "
                    f"{d['mode_paiement']}  "
                    f"{d.get('libelle','')}- "
                    f"{echeance}"
                )

                data.append([
                    "",
                    Paragraph(txt, style_produit),
                    "",
                    "",
                    ""
                ])

    # =========================
    # TOTAL FINAL
    # =========================
    data.append([
        "TOTAL",
        "",
        f"{total_debit:.3f}",
        f"{total_credit:.3f}",
        f"{solde:.3f}"
    ])


    table = Table(
        data,
        colWidths=[3*cm, 8*cm, 3*cm, 3*cm, 3*cm]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        ("FONTSIZE", (0,0), (-1,-1), 10),

        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),

        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
        # 🔥 ALIGNEMENT
        ("ALIGN", (0,0), (1,-1), "LEFT"),   # Date + Libellé
        ("ALIGN", (2,0), (-1,-1), "RIGHT")  # Débit + Crédit + Solde

    ]))

    elements.append(table)

    # SOLDE FINAL
    solde_style = ParagraphStyle(
        "solde_style",
        parent=styles["Normal"],
        fontSize=14,
    )

    elements.append(Spacer(1, 6))

    elements.append(
        Paragraph(
            f"<b>Solde Final : {solde:.3f} TND</b>",
            solde_style
        )
    )

    doc.build(elements)
    return response