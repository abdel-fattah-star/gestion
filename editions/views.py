from django.shortcuts import render, redirect
from django.utils import timezone
from ventes.models import BonLivraison, Facture, Client
from django.contrib.admin.views.decorators import staff_member_required
# ---------------- PDF ----------------
from django.shortcuts import render
from django.db.models import Sum
from ventes.models import BonLivraison
#from datetime import datetime
from core.models import Societe  # selon ton app

@staff_member_required
def dashboard_admin(request):
    """
    Dashboard ERP admin
    """
    return render(request, "editions/admin_dashboard.html")


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import now
from ventes.models import BonLivraison, Facture, LigneBonLivraison, LigneFacture, Client

def generer_numero_facture():
    annee = now().year
    prefix = f"FAC-{annee}-"
    derniere = Facture.objects.filter(numero__startswith=prefix).order_by("numero").last()
    if derniere and derniere.numero:
        try:
            num = int(derniere.numero.split("-")[-1]) + 1
        except ValueError:
            num = 1
    else:
        num = 1
    return f"{prefix}{num:05d}"

@staff_member_required
def facturation_globale(request):
    clients = Client.objects.all()
    bons = BonLivraison.objects.filter(facture__isnull=True).order_by("-date")
    
    # Filtre client / date
    client_id = request.GET.get("client")
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    if client_id:
        bons = bons.filter(client_id=client_id)
    if date_debut:
        bons = bons.filter(date__gte=date_debut)
    if date_fin:
        bons = bons.filter(date__lte=date_fin)

    facture_creee = None

    if request.method == "POST":
        bons_ids = request.POST.getlist("bons_ids")
        if not bons_ids:
            messages.warning(request, "Aucun bon sélectionné !")
            return redirect('facturation_globale')

        bons_selectionnes = bons.filter(id__in=bons_ids)
        if not bons_selectionnes.exists():
            messages.warning(request, "Les bons sélectionnés ont déjà été facturés !")
            return redirect('facturation_globale')

        client = bons_selectionnes.first().client
        numero = generer_numero_facture()

        # Création de la facture
        facture_creee = Facture.objects.create(
            numero=numero,
            client=client,
            date=now(),
            statut='brouillon',
            mf_client=bons_selectionnes.first().mf_client,
            adresse_client=bons_selectionnes.first().adresse_client,
            telephone_client=bons_selectionnes.first().telephone_client,
            email_client=bons_selectionnes.first().email_client
        )

        # Copier toutes les lignes de bons sélectionnés
        total_ht = total_rem = base_tva = total_tva = total_ttc = 0
        for bon in bons_selectionnes:
            for ligne in bon.lignes.all():
                montant_ht = ligne.quantite * ligne.prix_ht
                remise = montant_ht * (ligne.taux_rem / 100)
                base = montant_ht - remise
                tva = base * (ligne.taux_tva / 100)
                ttc = base + tva

                # Créer LigneFacture
                LigneFacture.objects.create(
                    facture=facture_creee,
                    produit=ligne.produit,
                    quantite=ligne.quantite,
                    prix_ht=ligne.prix_ht,
                    taux_rem=ligne.taux_rem,
                    taux_tva=ligne.taux_tva
                )

                # Cumuler totaux
                total_ht += montant_ht
                total_rem += remise
                base_tva += base
                total_tva += tva
                total_ttc += ttc

        # Mettre à jour la facture avec les totaux
        facture_creee.total_ht = total_ht
        facture_creee.total_rem = total_rem
        facture_creee.base_tva = base_tva
        facture_creee.total_tva = total_tva
        facture_creee.total_ttc = total_ttc
        facture_creee.save()

        # Lier les bons à la facture
        bons_selectionnes.update(facture=facture_creee, statut='validee')

        messages.success(request, f"Facture {facture_creee.numero} créée avec succès !")
        return redirect('facturation_globale')

    return render(request, "editions/facturation_globale.html", {
        "clients": clients,
        "bons": bons,
        "facture_creee": facture_creee
    })
#-----------   Facturation des bons selectionner
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.timezone import now
from ventes.models import BonLivraison, Facture

@staff_member_required
def facturer_bons(request):
    if request.method == "POST":
        # Récupérer les bons cochés
        bons_ids = request.POST.getlist("bons_ids")
        if not bons_ids:
            messages.warning(request, "Aucun bon sélectionné !")
            return redirect('facturation_globale')

        # Filtrer uniquement les bons non facturés
        bons = BonLivraison.objects.filter(id__in=bons_ids, facture__isnull=True)
        if not bons.exists():
            messages.warning(request, "Les bons sélectionnés ont déjà été facturés !")
            return redirect('facturation_globale')

        # On suppose que tous les bons sont du même client
        client = bons.first().client

        # Création de la facture
        facture = Facture.objects.create(
            client=client,
            date=now(),
            total_ht=sum(b.total_ht for b in bons),
            total_rem=sum(b.total_rem for b in bons),
            base_tva=sum(b.base_tva for b in bons),
            total_tva=sum(b.total_tva for b in bons),
            total_ttc=sum(b.total_ttc for b in bons),
            statut='brouillon',
            mf_client=bons.first().mf_client,
            adresse_client=bons.first().adresse_client,
            telephone_client=bons.first().telephone_client,
            email_client=bons.first().email_client,
        )

        # Lier les bons à la facture et marquer comme validée
        bons.update(facture=facture, statut='validee')

        messages.success(request, f"Facture {facture.numero or facture.id} créée avec succès !")
        return redirect('facturation_globale')

    return redirect('facturation_globale')




# ---------------- IMPORTS ----------------
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum
from ventes.models import BonLivraison, AvoirClient
from achats.models import AvoirFournisseur
from fpdf import FPDF


# ---------------- QUERYSET ----------------
def get_bons_queryset(date_debut, date_fin):
    bons = BonLivraison.objects.all()

    if date_debut:
        bons = bons.filter(date__gte=date_debut)

    if date_fin:
        bons = bons.filter(date__lte=date_fin)

    return bons.order_by("date")


# ---------------- HTML ----------------
def liste_bons_impression(request):
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    bons = get_bons_queryset(date_debut, date_fin)

    totaux = bons.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )

    # éviter None
    for k in totaux:
        totaux[k] = totaux[k] or 0

    return render(request, "editions/liste_bons_impression.html", {
        "bons": bons,
        "totaux": totaux,
        "date_debut": date_debut,
        "date_fin": date_fin,
    })

#------ Listes des bons d'avoir clients  Html
# ---------------- QUERYSET ----------------
def get_avoirs_queryset(date_debut, date_fin):
    bons =AvoirClient.objects.all()

    if date_debut:
        bons = bons.filter(date__gte=date_debut)

    if date_fin:
        bons = bons.filter(date__lte=date_fin)

    return bons.order_by("date")



def liste_avoirs_clients(request):
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    bons = get_avoirs_queryset(date_debut, date_fin)

    totaux = bons.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )

    # éviter None
    for k in totaux:
        totaux[k] = totaux[k] or 0

    return render(request, "editions/liste_avoirs_clients.html", {
        "bons": bons,
        "totaux": totaux,
        "date_debut": date_debut,
        "date_fin": date_fin,
    })

def liste_avoirs_clients_pdf(request):
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")
    
    # Queryset des bons comme avant
    bons = AvoirClient.objects.all()
    if date_debut:
        bons = bons.filter(date__gte=date_debut)
    if date_fin:
        bons = bons.filter(date__lte=date_fin)
    bons = bons.order_by("date")

    totaux = bons.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )
    for k in totaux:
        totaux[k] = totaux[k] or 0

    # Récupérer la société (ex: première)
    societe = Societe.objects.first()

    import datetime
    today = datetime.datetime.now()

    return render(request, "editions/liste_avoirs_clients_pdf.html", {
        "bons": bons,
        "totaux": totaux,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "societe": societe,
        "today": today,
    })


#------ Avoirs fournisseurs
def get_avoirs_fournisseurs_queryset(date_debut, date_fin):
    bons =AvoirFournisseur.objects.all()

    if date_debut:
        bons = bons.filter(date__gte=date_debut)

    if date_fin:
        bons = bons.filter(date__lte=date_fin)

    return bons.order_by("date")



def liste_avoirs_fournisseurs(request):
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    bons = get_avoirs_fournisseurs_queryset(date_debut, date_fin)

    totaux = bons.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )

    # éviter None
    for k in totaux:
        totaux[k] = totaux[k] or 0

    return render(request, "editions/liste_avoirs_fournisseurs.html", {
        "bons": bons,
        "totaux": totaux,
        "date_debut": date_debut,
        "date_fin": date_fin,
    })

def liste_avoirs_fournisseurs_pdf(request):
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")
    
    # Queryset des bons comme avant
    bons = AvoirFournisseur.objects.all()
    if date_debut:
        bons = bons.filter(date__gte=date_debut)
    if date_fin:
        bons = bons.filter(date__lte=date_fin)
    bons = bons.order_by("date")

    totaux = bons.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )
    for k in totaux:
        totaux[k] = totaux[k] or 0

    # Récupérer la société (ex: première)
    societe = Societe.objects.first()

    import datetime
    today = datetime.datetime.now()

    return render(request, "editions/liste_avoirs_fournisseurs_pdf.html", {
        "bons": bons,
        "totaux": totaux,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "societe": societe,
        "today": today,
    })


#------ Fin

def liste_bons_pdf(request):
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")
    
    # Queryset des bons comme avant
    bons = BonLivraison.objects.all()
    if date_debut:
        bons = bons.filter(date__gte=date_debut)
    if date_fin:
        bons = bons.filter(date__lte=date_fin)
    bons = bons.order_by("date")

    totaux = bons.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )
    for k in totaux:
        totaux[k] = totaux[k] or 0

    # Récupérer la société (ex: première)
    societe = Societe.objects.first()

    import datetime
    today = datetime.datetime.now()

    return render(request, "editions/liste_bons_pdf.html", {
        "bons": bons,
        "totaux": totaux,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "societe": societe,
        "today": today,
    })


#-------------------- Liste des factures

# ---------------- HTML ----------------

def liste_factures_impression(request):

    from django.shortcuts import render
    from django.db.models import Sum
    from ventes.models import Facture
    from core.models import Societe
    import datetime



    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    factures = Facture.objects.all()

    if date_debut:
        factures = factures.filter(date__gte=date_debut)
    if date_fin:
        factures = factures.filter(date__lte=date_fin)

    factures = factures.order_by("date")

    total_r_source = 0

    for f in factures:
        ttc = f.total_ttc or 0
        ttc = float(ttc)   # 🔥 important

        if ttc >= 1000:
            f.r_source = round((ttc - 1) * 0.01, 3)
        else:
            f.r_source = 0

        total_r_source += f.r_source

    totaux = factures.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )

    for k in totaux:
        totaux[k] = totaux[k] or 0

    societe = Societe.objects.first()
    today = datetime.datetime.now()

    return render(request, "editions/liste_factures_impression.html", {
        "factures": factures,
        "totaux": totaux,
        "total_r_source": total_r_source,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "societe": societe,
        "today": today,
    })

def liste_factures_pdf(request):

    from django.shortcuts import render
    from django.db.models import Sum
    from ventes.models import Facture  # Remplacer BonLivraison par Facture
    from core.models import Societe
    import datetime


    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")
    
    # Queryset des factures
    factures = Facture.objects.all()
    if date_debut:
        factures = factures.filter(date__gte=date_debut)
    if date_fin:
        factures = factures.filter(date__lte=date_fin)
    factures = factures.order_by("date")

    total_r_source = 0

    for f in factures:
        ttc = f.total_ttc or 0
        ttc = float(ttc)   # 🔥 important

        if ttc >= 1000:
            f.r_source = round((ttc - 1) * 0.01, 3)
        else:
            f.r_source = 0

        total_r_source += f.r_source

    totaux = factures.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )
    for k in totaux:
        totaux[k] = totaux[k] or 0

    societe = Societe.objects.first()
    today = datetime.datetime.now()

    return render(request, "editions/liste_factures_pdf.html", {
        "factures": factures,
        "totaux": totaux,
        "total_r_source": total_r_source,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "societe": societe,
        "today": today,
    })

#--------------------------------------- 

# ----------------Factures achats  HTML ----------------

def liste_factachats_impression(request):

    from django.shortcuts import render
    from django.db.models import Sum
    from fournisseurs.models import Fournisseur
    from achats.models import FactureAchat
    from core.models import Societe
    import datetime

    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    factures = FactureAchat.objects.all()

    if date_debut:
        factures = factures.filter(date__gte=date_debut)
    if date_fin:
        factures = factures.filter(date__lte=date_fin)

    factures = factures.order_by("date")

    total_r_source = 0
    totaux_net_servi = 0

    for f in factures:

        ttc = float(f.total_ttc or 0)

        fournisseur = Fournisseur.objects.filter(
            matricule_fiscal=f.mf_fournisseur
        ).first()

        # =========================
        # DEFAULT PM
        # =========================
        taux_rs = 0.01

        # =========================
        # IF PP
        # =========================
        if fournisseur and fournisseur.type_contribuable == "PP":
            taux_rs = 0.015

        # =========================
        # CALCUL
        # =========================
        if ttc >= 1000:
            f.r_source = round((ttc - 1) * taux_rs, 3)
            f.net_servi = round(ttc - f.r_source, 3)
        else:
            f.r_source = 0
            f.net_servi  = 0

        total_r_source += f.r_source
        totaux_net_servi += f.net_servi

    totaux = factures.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )

    for k in totaux:
        totaux[k] = totaux[k] or 0

    societe = Societe.objects.first()
    today = datetime.datetime.now()

    return render(request, "editions/liste_factachats_impression.html", {
        "factures": factures,
        "totaux": totaux,
        "total_r_source": total_r_source,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "societe": societe,
        "today": today,
        "totaux_net_servi": totaux_net_servi,
    })

def liste_factachats_pdf(request):

    from django.shortcuts import render
    from django.db.models import Sum
    from achats.models import FactureAchat
    from core.models import Societe
    import datetime
    from fournisseurs.models import Fournisseur

    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")
    
    # Queryset des factures
    factures = FactureAchat.objects.all()
    if date_debut:
        factures = factures.filter(date__gte=date_debut)
    if date_fin:
        factures = factures.filter(date__lte=date_fin)

    factures = factures.order_by("date")

    total_r_source = 0
    totaux_net_servi = 0

    for f in factures:

        ttc = float(f.total_ttc or 0)

        fournisseur = Fournisseur.objects.filter(
            matricule_fiscal=f.mf_fournisseur
        ).first()

        # =========================
        # DEFAULT PM
        # =========================
        taux_rs = 0.01

        # =========================
        # IF PP
        # =========================
        if fournisseur and fournisseur.type_contribuable == "PP":
            taux_rs = 0.015

        # =========================
        # CALCUL
        # =========================
        if ttc >= 1000:
            f.r_source = round((ttc - 1) * taux_rs, 3)
            f.net_servi = round(ttc - f.r_source, 3)
        else:
            f.r_source = 0
            f.net_servi = 0

        total_r_source += f.r_source
        totaux_net_servi += f.net_servi


    totaux = factures.aggregate(
        total_ht=Sum("total_ht"),
        total_rem=Sum("total_rem"),
        base_tva=Sum("base_tva"),
        total_tva=Sum("total_tva"),
        total_ttc=Sum("total_ttc"),
    )
    for k in totaux:
        totaux[k] = totaux[k] or 0

    societe = Societe.objects.first()
    today = datetime.datetime.now()

    return render(request, "editions/liste_factachats_pdf.html", {
        "factures": factures,
        "totaux": totaux,
        "total_r_source": total_r_source,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "societe": societe,
        "today": today,
        "totaux_net_servi": totaux_net_servi,
    })

#-----------------------------  Fichier xml


def export_factachats_xml(request):

    import os
    import xml.etree.ElementTree as ET

    from decimal import Decimal, ROUND_HALF_UP
    from datetime import datetime

    from django.conf import settings
    from django.http import HttpResponse

    from achats.models import FactureAchat

    # =====================================================
    # PARAMETRES
    # =====================================================

    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    if not date_debut or not date_fin:
        return HttpResponse(
            "Dates manquantes",
            status=400
        )

    date_debut = datetime.strptime(
        date_debut,
        "%Y-%m-%d"
    ).date()

    date_fin = datetime.strptime(
        date_fin,
        "%Y-%m-%d"
    ).date()

    MATRICULE_DECLARANT = "1448066K"

    CODE_ACTE = "0"

    exercice = date_debut.strftime("%Y")
    mois = date_debut.strftime("%m")

    # =====================================================
    # FACTURES
    # =====================================================

    factures = FactureAchat.objects.filter(
        date__range=(date_debut, date_fin),
        total_ht__isnull=False,
        total_ht__gt=0
    ).exclude(statut="payee").order_by("date")


    # =====================================================
    # HELPERS
    # =====================================================

    def clean(value):
        return str(value).strip() if value else ""

    def to_millimes(value):
        """
        123.456 -> 123456
        """

        value = Decimal(
            str(value or 0)
        )

        return int(
            (value * 1000).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

    def taux(value):

        value = Decimal(
            str(value or 0)
        ).quantize(
            Decimal("0.00"),
            rounding=ROUND_HALF_UP
        )

        return f"{value:06.2f}"

    # =====================================================
    # ROOT
    # =====================================================

    root = ET.Element(
        "DeclarationsRS",
        VersionSchema="1.0"
    )

    # =====================================================
    # DECLARANT
    # =====================================================

    declarant = ET.SubElement(
        root,
        "Declarant"
    )

    ET.SubElement(
        declarant,
        "TypeIdentifiant"
    ).text = "1"

    ET.SubElement(
        declarant,
        "Identifiant"
    ).text = MATRICULE_DECLARANT

    ET.SubElement(
        declarant,
        "CategorieContribuable"
    ).text = "PM"

    # =====================================================
    # REFERENCE DECLARATION
    # =====================================================

    reference = ET.SubElement(
        root,
        "ReferenceDeclaration"
    )

    ET.SubElement(
        reference,
        "ActeDepot"
    ).text = CODE_ACTE

    ET.SubElement(
        reference,
        "AnneeDepot"
    ).text = exercice

    ET.SubElement(
        reference,
        "MoisDepot"
    ).text = mois

    # =====================================================
    # CERTIFICATS
    # =====================================================

    ajouter_certificats = ET.SubElement(
        root,
        "AjouterCertificats"
    )

    # =====================================================
    # BOUCLE FACTURES
    # =====================================================

    for facture in factures:

        fournisseur = facture.fournisseur

        mf = clean(
            facture.mf_fournisseur
        ).upper()

        nom = clean(
            fournisseur.nom if fournisseur else ""
        )

        type_contrib = (
            fournisseur.type_contribuable
            if fournisseur and fournisseur.type_contribuable
            else "PM"
        )

        TAUX_TVA = Decimal("19.00")

        if type_contrib == "PM":
            TAUX_RS = Decimal("1.00")
        else:
            TAUX_RS = Decimal("1.50")

        # =================================================
        # MONTANTS EN MILLIMES
        # =================================================

        # HT exact saisi utilisateur
        ht_m = int(
            Decimal(
                str(facture.base_tva or 0)
            ) * 1000
        )

        TAUX_TVA_INT = 19

        if type_contrib == "PM":
            TAUX_RS_INT = 1
        else:
            TAUX_RS_INT = 1.5

        # TVA : TRONCATURE
        tva_m = int(
            ht_m * TAUX_TVA_INT / 100
        )

        # TTC
        ttc_m = ht_m + tva_m

        # RS : TRONCATURE
        rs_m = int(
            ttc_m * TAUX_RS_INT / 100
        )

        # NET
        net_m = ttc_m - rs_m

        # =================================================
        # CERTIFICAT
        # =================================================

        certificat = ET.SubElement(
            ajouter_certificats,
            "Certificat"
        )

        # =================================================
        # BENEFICIAIRE
        # =================================================

        beneficiaire = ET.SubElement(
            certificat,
            "Beneficiaire"
        )

        id_taxpayer = ET.SubElement(
            beneficiaire,
            "IdTaxpayer"
        )

        matricule_fiscal = ET.SubElement(
            id_taxpayer,
            "MatriculeFiscal"
        )

        ET.SubElement(
            matricule_fiscal,
            "TypeIdentifiant"
        ).text = "1"

        ET.SubElement(
            matricule_fiscal,
            "Identifiant"
        ).text = mf

        ET.SubElement(
            matricule_fiscal,
            "CategorieContribuable"
        ).text = type_contrib

        ET.SubElement(
            beneficiaire,
            "Resident"
        ).text = "1"

        ET.SubElement(
            beneficiaire,
            "NometprenonOuRaisonsociale"
        ).text = nom

        ET.SubElement(
            beneficiaire,
            "Adresse"
        ).text = clean(
            facture.adresse_fournisseur
        )

        infos_contact = ET.SubElement(
            beneficiaire,
            "InfosContact"
        )

        ET.SubElement(
            infos_contact,
            "AdresseMail"
        ).text = clean(
            facture.email_fournisseur
        )

        ET.SubElement(
            infos_contact,
            "NumTel"
        ).text = clean(
            facture.telephone_fournisseur
        )

        # =================================================
        # INFOS CERTIFICAT
        # =================================================

        ET.SubElement(
            certificat,
            "DatePayement"
        ).text = facture.date.strftime(
            "%d/%m/%Y"
        )

        ET.SubElement(
            certificat,
            "Ref_certif_chez_declarant"
        ).text = clean(
            facture.numero
        )

        # =================================================
        # OPERATIONS
        # =================================================

        liste_operations = ET.SubElement(
            certificat,
            "ListeOperations"
        )

        operation = ET.SubElement(
            liste_operations,
            "Operation",
            IdTypeOperation="RS7_000002"
        )

        ET.SubElement(
            operation,
            "AnneeFacturation"
        ).text = str(
            facture.date.year
        )

        ET.SubElement(
            operation,
            "CNPC"
        ).text = "0"

        ET.SubElement(
            operation,
            "P_Charge"
        ).text = "0"

        ET.SubElement(
            operation,
            "MontantHT"
        ).text = str(
            ht_m
        )

        ET.SubElement(
            operation,
            "TauxRS"
        ).text = taux(
            TAUX_RS
        )

        ET.SubElement(
            operation,
            "TauxTVA"
        ).text = taux(
            TAUX_TVA
        )

        ET.SubElement(
            operation,
            "MontantTVA"
        ).text = str(
            tva_m
        )

        ET.SubElement(
            operation,
            "MontantTTC"
        ).text = str(
            ttc_m
        )

        ET.SubElement(
            operation,
            "MontantRS"
        ).text = str(
            rs_m
        )

        ET.SubElement(
            operation,
            "MontantNetServi"
        ).text = str(
            net_m
        )

        # =================================================
        # TOTAL PAIEMENT
        # =================================================

        total_payement = ET.SubElement(
            certificat,
            "TotalPayement"
        )

        ET.SubElement(
            total_payement,
            "TotalMontantHT"
        ).text = str(
            ht_m
        )

        ET.SubElement(
            total_payement,
            "TotalMontantTVA"
        ).text = str(
            tva_m
        )

        ET.SubElement(
            total_payement,
            "TotalMontantTTC"
        ).text = str(
            ttc_m
        )

        ET.SubElement(
            total_payement,
            "TotalMontantRS"
        ).text = str(
            rs_m
        )

        ET.SubElement(
            total_payement,
            "TotalMontantNetServi"
        ).text = str(
            net_m
        )

    # =====================================================
    # SAUVEGARDE
    # =====================================================

    filename = (
        f"{MATRICULE_DECLARANT}-"
        f"{exercice}-{mois}-{CODE_ACTE}.xml"
    )

    media_dir = os.path.join(
        settings.MEDIA_ROOT,
        "xml_exports"
    )

    os.makedirs(
        media_dir,
        exist_ok=True
    )

    file_path = os.path.join(
        media_dir,
        filename
    )

    tree = ET.ElementTree(root)

    tree.write(
        file_path,
        encoding="utf-8",
        xml_declaration=True
    )

    # =====================================================
    # DOWNLOAD
    # =====================================================

    response = HttpResponse(
        content_type="application/xml"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{filename}"'
    )

    tree.write(
        response,
        encoding="utf-8",
        xml_declaration=True
    )

    return response

#----------------------------- Fin
