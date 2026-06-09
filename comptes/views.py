# comptes/views.py

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph
from .models import Compte
from reglements.models import MouvementCompte
from core.models import Societe
from django.utils.dateparse import parse_date
from core.report_styles import STYLE_LIBELLE

# ------------------- UTILITAIRE -------------------
def calcul_mouvements_solde(compte, date_debut=None, date_fin=None):
    """
    Retourne mouvements filtrés, report initial, totaux et solde final
    """
    mouvements = MouvementCompte.objects.filter(compte=compte).order_by("date")

    # Report initial avant date_debut
    report = 0
    if date_debut:
        mouvements_avant = mouvements.filter(date__lt=date_debut)
        report = sum(
            m.montant if m.type_mouvement == "entree" else -m.montant
            for m in mouvements_avant
        )

    # Filtrer selon période
    if date_debut:
        mouvements = mouvements.filter(date__gte=date_debut)
    if date_fin:
        mouvements = mouvements.filter(date__lte=date_fin)

    solde = report
    total_debit = 0
    total_credit = 0
    lignes = []

    for m in mouvements:
        debit = m.montant if m.type_mouvement == "entree" else 0
        credit = m.montant if m.type_mouvement == "sortie" else 0
        solde += debit - credit
        total_debit += debit
        total_credit += credit

        # Libellé détaillé si règlement client/fournisseur
        if hasattr(m, "reglement_client") and m.reglement_client:
            libelle = (
                f"Règlement Client "
                f"{m.reglement_client.client.nom}"
            )

        elif hasattr(m, "reglement_fournisseur") and m.reglement_fournisseur:
            libelle = (
                f"Règlement Fournisseur "
                f"{m.reglement_fournisseur.fournisseur.nom}"
            )

        else:
            libelle = m.reference or f"MC n°{m.id}"

        lignes.append({
            "date": m.date,
            "libelle": libelle,
            "debit": debit,
            "credit": credit,
            "solde": solde
        })

    return lignes, report, total_debit, total_credit, solde

# ------------------- VUES -------------------
def releve_compte(request, compte_id):
    compte = get_object_or_404(Compte, id=compte_id)
    societe = Societe.objects.first()

    # Récupérer dates depuis le HTML
    date_debut_str = request.GET.get("date_debut")
    date_fin_str = request.GET.get("date_fin")
    date_debut = parse_date(date_debut_str) if date_debut_str else None
    date_fin = parse_date(date_fin_str) if date_fin_str else None

    lignes, report, total_debit, total_credit, solde = calcul_mouvements_solde(
        compte, date_debut, date_fin
    )

    context = {
        "societe": societe,
        "compte": compte,
        "lignes": lignes,
        "report": report,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "solde": solde,
        "date_debut": date_debut_str,
        "date_fin": date_fin_str
    }

    return render(request, "comptes/releve_compte.html", context)


def releve_compte_pdf(request, compte_id):
    compte = get_object_or_404(Compte, id=compte_id)
    societe = Societe.objects.first()

    # Récupérer dates depuis le HTML
    date_debut_str = request.GET.get("date_debut")
    date_fin_str = request.GET.get("date_fin")
    date_debut = parse_date(date_debut_str) if date_debut_str else None
    date_fin = parse_date(date_fin_str) if date_fin_str else None

    lignes, report, total_debit, total_credit, solde = calcul_mouvements_solde(
        compte, date_debut, date_fin
    )

    # Création du PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename=releve_compte_{compte.id}.pdf"

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 2*cm

    # Entête société
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1*cm, y, societe.nom if societe else "Société")
    y -= 0.6*cm
    p.setFont("Helvetica", 10)
    if societe:
        p.drawString(1*cm, y, societe.adresse or "")
        y -= 0.6*cm
        p.drawString(1*cm, y, "M.F : " + (societe.matricule_fiscal or "").upper())
        y -= 0.6*cm

        p.drawString(1*cm, y, f"Tél: {societe.telephone or ''} - Email: {societe.email or ''}")
    y -= 1*cm
    p.setFont("Helvetica-Bold", 14)
    p.drawString(6*cm, y, f"Releve de compte : {compte.libelle or ''}")
    y -= 2*cm

    # Report initial
    p.setFont("Helvetica-Bold", 11)
    p.drawString(2*cm, y, f"Report initial : {report:.3f}")
    y -= 0.6*cm

    # Période
    periode_text = "Période : "
    if date_debut and date_fin:
        periode_text += f"{date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
    elif date_debut:
        periode_text += f"à partir de {date_debut.strftime('%d/%m/%Y')}"
    elif date_fin:
        periode_text += f"jusqu'à {date_fin.strftime('%d/%m/%Y')}"
    else:
        periode_text += "tous les mouvements"
    p.setFont("Helvetica", 10)
    p.drawString(2*cm, y, periode_text)
    y -= 0.8*cm

    # Tableau
    data = [["Date", "Libellé", "Débit", "Crédit", "Solde"]]
    for l in lignes:
        data.append([
            l["date"].strftime("%d/%m/%Y"),
            Paragraph(l["libelle"], STYLE_LIBELLE),
            f"{l['debit']:.3f}" if l["debit"] else "",
            f"{l['credit']:.3f}" if l["credit"] else "",
            f"{l['solde']:.3f}"
        ])
    # Totaux
    data.append(["Totaux", "", f"{total_debit:.3f}", f"{total_credit:.3f}", f"{solde:.3f}"])

    table = Table(data, colWidths=[3*cm, 6*cm, 3*cm, 3*cm, 3*cm])    
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (2,0), (-1,-1), "RIGHT"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
    ]))

    w, h = table.wrapOn(p, width-4*cm, y)
    table.drawOn(p, 1.5*cm, y-h)

    
    
    p.showPage()
    p.save()

    return response

#--------- Releve non echu

from datetime import date
from reglements.models import ReglementClient, ReglementFournisseur

def calcul_non_echu(compte, date_debut=None, date_fin=None):
    today = date.today()

    # -------- CLIENTS --------
    rc = ReglementClient.objects.filter(
        compte=compte,
        echeance__gt=today
    )

    if date_debut:
        rc = rc.filter(date__gte=date_debut)
    if date_fin:
        rc = rc.filter(date__lte=date_fin)

    # -------- FOURNISSEURS --------
    rf = ReglementFournisseur.objects.filter(
        compte=compte,
        echeance__gt=today
    )

    if date_debut:
        rf = rf.filter(date__gte=date_debut)
    if date_fin:
        rf = rf.filter(date__lte=date_fin)

    # -------- LIGNES --------
    lignes = []

    for r in rc:
        lignes.append({
            "date": r.date,
            "mode": r.mode_paiement or "",
            "reference": r.libelle or "",   # ✅ IMPORTANT
            "echeance": r.echeance,
            "debit": r.montant,
            "credit": 0,
        })

    for r in rf:
        lignes.append({
            "date": r.date,
            "mode": r.mode_paiement or "",
            "reference": r.libelle or "",   # ✅ IMPORTANT
            "echeance": r.echeance,
            "debit": 0,
            "credit": r.montant,
        })

    # tri
    lignes.sort(key=lambda x: x["date"])

    total_debit = sum(l["debit"] for l in lignes)
    total_credit = sum(l["credit"] for l in lignes)
    solde = total_debit - total_credit

    return lignes, total_debit, total_credit, solde

from datetime import date
from datetime import date
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date

from datetime import date
from django.utils.dateparse import parse_date

def releve_non_echu(request, compte_id):
    compte = get_object_or_404(Compte, id=compte_id)
    societe = Societe.objects.first()

    date_debut_str = request.GET.get("date_debut")
    date_fin_str = request.GET.get("date_fin")

    date_debut = parse_date(date_debut_str) if date_debut_str else None
    date_fin = parse_date(date_fin_str) if date_fin_str else None

    # base query
    rc = ReglementClient.objects.filter(compte=compte)
    rf = ReglementFournisseur.objects.filter(compte=compte)

    # 🔥 FILTRE ÉCHÉANCE (LOGIQUE DEMANDÉE)
    if date_debut:
        rc = rc.filter(echeance__gte=date_debut)
        rf = rf.filter(echeance__gte=date_debut)

    if date_fin:
        rc = rc.filter(echeance__lte=date_fin)
        rf = rf.filter(echeance__lte=date_fin)

    lignes = []

    # CLIENTS
    for r in rc:
        lignes.append({
            "nom": r.client.nom if r.client else "",
            "mode": r.mode_paiement or "",
            "reference": r.libelle or "",
            "echeance": r.echeance,
            "debit": r.montant,
            "credit": 0,
        })

    # FOURNISSEURS
    for r in rf:
        lignes.append({
            "nom": r.fournisseur.nom if r.fournisseur else "",
            "mode": r.mode_paiement or "",
            "reference": r.libelle or "",
            "echeance": r.echeance,
            "debit": 0,
            "credit": r.montant,
        })

    lignes.sort(key=lambda x: x["echeance"] or date.today())

    total_debit = sum(l["debit"] for l in lignes)
    total_credit = sum(l["credit"] for l in lignes)

    return render(request, "comptes/releve_non_echu.html", {
        "societe": societe,
        "compte": compte,
        "lignes": lignes,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "date_debut": date_debut_str,
        "date_fin": date_fin_str,
        "titre": "Relevé échéances"
    })


from datetime import date
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

def releve_non_echu_pdf(request, compte_id):

    compte = get_object_or_404(Compte, id=compte_id)
    societe = Societe.objects.first()

    date_debut = parse_date(request.GET.get("date_debut")) if request.GET.get("date_debut") else None
    date_fin = parse_date(request.GET.get("date_fin")) if request.GET.get("date_fin") else None

    today = date.today()

    # ---------------- DATA ----------------
    rc = ReglementClient.objects.filter(compte=compte)
    rf = ReglementFournisseur.objects.filter(compte=compte)

    if date_debut:
        rc = rc.filter(echeance__gte=date_debut)
        rf = rf.filter(echeance__gte=date_debut)

    if date_fin:
        rc = rc.filter(echeance__lte=date_fin)
        rf = rf.filter(echeance__lte=date_fin)

    lignes = []

    for r in rc:
        lignes.append({
            "nom": r.client.nom if r.client else "",
            "mode": r.mode_paiement or "",
            "reference": r.libelle or "",
            "echeance": r.echeance,
            "debit": r.montant,
            "credit": 0,
        })

    for r in rf:
        lignes.append({
            "nom": r.fournisseur.nom if r.fournisseur else "",
            "mode": r.mode_paiement or "",
            "reference": r.libelle or "",
            "echeance": r.echeance,
            "debit": 0,
            "credit": r.montant,
        })

    lignes.sort(key=lambda x: x["echeance"] or today)

    total_debit = sum(l["debit"] for l in lignes)
    total_credit = sum(l["credit"] for l in lignes)

    # ---------------- PDF ----------------
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=releve_echeances.pdf"

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 2*cm

    p.setFont("Helvetica-Bold", 13)
    p.drawString(1*cm, y, societe.nom if societe else "Société")
    y -= 0.5*cm

    p.setFont("Helvetica", 9)
    p.drawString(1*cm, y, societe.adresse or "")
    y -= 0.4*cm

    p.drawString(1*cm, y, "M.F : " + (societe.matricule_fiscal or "").upper())
    y -= 0.6*cm
    # ================= TITLE =================
    p.setFont("Helvetica-Bold", 14)
    p.drawString(7*cm, y, "Échéances de la période")
    y -= 0.5*cm

    p.setFont("Helvetica", 9)
    p.drawString(1*cm, y, f"Période : {date_debut or ''} au {date_fin or ''}")
    y -= 0.8*cm

    # ================= COLOR LOGIC =================
    def get_color(echeance):
        if not echeance:
            return colors.black
        diff = (echeance - today).days
        if diff <= 3:
            return colors.red
        elif diff <= 7:
            return colors.orange
        return colors.black

    # ================= TABLE =================
    data = [["Nom", "Mode", "Référence", "Échéance", "Débit", "Crédit"]]

    style = TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (4,0), (-1,-1), "RIGHT"),
    ])

    for i, l in enumerate(lignes, start=1):

        data.append([
            l["nom"],
            l["mode"],
            l["reference"],
            l["echeance"].strftime("%d/%m/%Y") if l["echeance"] else "",
            f"{l['debit']:.3f}" if l["debit"] else "",
            f"{l['credit']:.3f}" if l["credit"] else "",
        ])

        style.add("TEXTCOLOR", (0, i), (-1, i), get_color(l["echeance"]))

    # totaux
    data.append(["", "", "Totaux", "", f"{total_debit:.3f}", f"{total_credit:.3f}"])
    style.add("FONTNAME", (0, len(data)-1), (-1, -1), "Helvetica-Bold")

    # largeur paysage (IMPORTANT)
    table = Table(data, colWidths=[5*cm, 3*cm, 5*cm, 2*cm, 2*cm, 2*cm])

    table.setStyle(style)

    table.wrapOn(p, width, height)
    table.drawOn(p, 1*cm, y - table._height)

    p.showPage()
    p.save()

    return response