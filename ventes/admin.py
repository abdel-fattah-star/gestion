from django.contrib import admin, messages
from django.urls import reverse, path
from django.utils.html import format_html
from django.shortcuts import redirect
from django.db.models import Max
from .models import BonLivraison, LigneBonLivraison
from .models import Facture, LigneFacture, Devis, LigneDevis
from  django.contrib.auth.models import User, Group
from django.contrib import admin
from django.utils.html import format_html
from produits.models import Produit
from ventes.models import LigneBonLivraison
from achats.models import LigneBonReception


# ===============================
# INLINE LIGNES DEVIS
# ===============================
#@admin.register(LigneDevis)
class LigneDevisInline(admin.TabularInline):
    model = LigneDevis
    extra = 1
    fields = (
        "produit",
        "quantite",
        "prix_ht",
        "taux_rem",
        "taux_tva",
    )


# ===============================
# ADMIN DEVIS
# ===============================

class DevisAdmin(admin.ModelAdmin):

    class Media:
        js = (
            "ventes/client_auto.js",
         )

    
    inlines = [LigneDevisInline]

    list_display = (
        "numero",
        "client",
        "statut",
        "date",
        "bouton_pdf",
    )

    fields = (
        "numero",
        "date",
        "client",
        "mf_client",
        "adresse_client",
        "telephone_client",
        "email_client",
        "statut",
    )
    search_fields = (
        "numero",
        "client__nom",
    )

    readonly_fields = (
        "numero",
    )

    # ===============================
    # NUMERO AUTO
    # ===============================
    def save_model(self, request, obj, form, change):

        if not obj.numero:

            dernier = Devis.objects.aggregate(Max("numero"))

            if dernier["numero__max"]:
                obj.numero = str(int(dernier["numero__max"]) + 1)
            else:
                obj.numero = "1"

        super().save_model(request, obj, form, change)

    # ===============================
    # TOTAL TTC CALCULE
    # ===============================
    def afficher_total_ttc(self, obj):

        total = 0

        for ligne in obj.lignes.all():

            montant_ht = ligne.quantite * ligne.prix_ht
            rem = montant_ht * (ligne.taux_rem or 0) / 100
            base = montant_ht - rem
            tva = base * (ligne.taux_tva or 0) / 100

            total += base + tva

        return f"{total:.3f} TND"

    afficher_total_ttc.short_description = "Total TTC"

    # ===============================
    # BOUTON PDF
    # ===============================
    def bouton_pdf(self, obj):

        url = reverse("devis_pdf", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" target="_blank" '
            'style="background:#007bff;color:white;padding:4px 8px;border-radius:4px;">'
            'PDF</a>', url
        )

    bouton_pdf.short_description = "PDF"

    # ===============================
    # JS CLIENT AUTO
    # ===============================


admin.site.register(Devis, DevisAdmin)


# ===============================
# INLINE LIGNES FACTURE
# ===============================

class LigneFactureInline(admin.TabularInline):
    model = LigneFacture
    extra = 1


# ===============================
# ADMIN FACTURE
# ===============================
#@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):

    class Media:
        js = (
            "ventes/client_auto.js",
        )


    inlines = [LigneFactureInline]

    list_display = (
        "numero",
        "client",
        "statut",
        "date",
        "total_ttc",
        "statut_colore",
        "bouton_valider",
        "bouton_pdf",
        "bouton_xml",
        "bouton_email",
    )

    fields = (
        "numero",
        "date",
        "client",
        "mf_client",
        "adresse_client",
        "telephone_client",
        "email_client",
        "statut",
    )
    search_fields = (
        "numero",
        "client__nom",
    )

    readonly_fields = (
        "numero",
    )

    # ===============================
    # TOTAL DYNAMIQUE
    # ===============================
    def total_ttc(self, obj):
        totaux = obj.calculer_totaux()
        if totaux and totaux["total_ttc"] is not None:
            return f"{totaux['total_ttc']:.3f} TND"
        return "0.000 TND"

    total_ttc.short_description = "Total TTC"

    # ===============================
    # STATUT COULEUR
    # ===============================
    def statut_colore(self, obj):
        couleurs = {
            "brouillon": "gray",
            "validee": "green",
            "payee": "blue",
        }

        return format_html(
            '<b style="color:{}">{}</b>',
            couleurs.get(obj.statut, "black"),
            obj.get_statut_display()
        )

    statut_colore.short_description = "Statut"

    # ===============================
    # BOUTON VALIDER
    # ===============================
    def bouton_valider(self, obj):

        if obj.statut == "validee":
            return "✔ Validée"

        url = reverse("admin:valider_facture", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" '
            'style="background:#28a745;color:white;padding:4px 8px;border-radius:4px;">'
            'Valider</a>', url
        )

    bouton_valider.short_description = "Valider"

    # ===============================
    # BOUTON PDF
    # ===============================
    def bouton_pdf(self, obj):

        url = reverse("facture_pdf", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" target="_blank" '
            'style="background:#007bff;color:white;padding:4px 8px;border-radius:4px;">'
            'PDF</a>', url
        )

    bouton_pdf.short_description = "PDF"

    # ===============================
    # BOUTON XML
    # ===============================
    def bouton_xml(self, obj):

        url = reverse("facture_xml", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" target="_blank" '
            'style="background:#6f42c1;color:white;padding:4px 8px;border-radius:4px;">'
            'XML</a>', url
        )

    bouton_xml.short_description = "XML"

    # ===============================
    # BOUTON EMAIL
    # ===============================
    def bouton_email(self, obj):

        url = reverse("envoyer_facture", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" '
            'style="background:#fd7e14;color:white;padding:4px 8px;border-radius:4px;">'
            'Email</a>', url
        )

    bouton_email.short_description = "Email"

    # ===============================
    # URL VALIDATION
    # ===============================
    def get_urls(self):

        urls = super().get_urls()

        custom = [
            path(
                "valider/<int:facture_id>/",
                self.admin_site.admin_view(self.valider_view),
                name="valider_facture",
            ),
        ]

        return custom + urls

    def valider_view(self, request, facture_id):

        facture = Facture.objects.get(id=facture_id)

        facture.valider()

        self.message_user(request, "Facture validée ✔", messages.SUCCESS)

        return redirect("/admin/ventes/facture/")

admin.site.register(Facture, FactureAdmin)


# ===============================
# ADMIN LIGNE FACTURE
# ===============================
@admin.register(LigneFacture)
class LigneFactureAdmin(admin.ModelAdmin):

    list_display = (
        "facture",
        "produit",
        "taux_rem",
        "quantite",
        "prix_ht",
        "taux_tva",
    )


# ===============================
# INLINE LIGNES BON LIVRAISON
# ===============================
#@admin.register(BonLivraison)
class LigneBonLivraisonInline(admin.TabularInline):
    model = LigneBonLivraison
    extra = 1

    class Media:
        js = (
            "ventes/client_auto.js",
            "ventes/stock.js",
        )

    
    fields = ("produit", "quantite", "prix_ht", "stock_affiche")
    readonly_fields = ("stock_affiche",)

    def stock_affiche(self, obj):
        return "-"   # valeur par défaut (important)

    stock_affiche.short_description = "Stock actuel"


# ===============================
# ADMIN BON LIVRAISON
# ===============================
@admin.register(BonLivraison)
class BonLivraisonAdmin(admin.ModelAdmin):
      

    inlines = [LigneBonLivraisonInline]

    list_display = (
        "numero",
        "client",
        "statut",
        "adresse_client",
        "telephone_client",
        "email_client",
        "total_ttc",
        "bouton_pdf",
    )
    fields = (
        "numero",
        "date",
        "client",
        "mf_client",
        "adresse_client",
        "telephone_client",
        "email_client",
        "statut",
    )
    search_fields = (
        "numero",
        "client__nom",
    )

    readonly_fields=(
        "numero",
        )
    # ===============================
    # TOTAL DYNAMIQUE
    # ===============================
    def total_ttc(self, obj):
        totaux = obj.calculer_totaux()
        if totaux and totaux["total_ttc"] is not None:
            return f"{totaux['total_ttc']:.3f} TND"
        return "0.000 TND"

    total_ttc.short_description = "Total TTC"

    # ===============================
    # STATUT COULEUR
    # ===============================

    # ===============================
    # BOUTON PDF
    # ===============================
    def bouton_pdf(self, obj):

        url = reverse("bl_pdf", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" target="_blank" '
            'style="background:#007bff;color:white;padding:4px 8px;border-radius:4px;">'
            'PDF</a>', url
        )

    bouton_pdf.short_description = "PDF"

    # ===============================
    # URL VALIDATION
    # ===============================
    def get_urls(self):

        urls = super().get_urls()

        custom = [
            path(
                "valider/<int:bon_id>/",
                self.admin_site.admin_view(self.valider_view),
                name="valider_bonlivraison",
            ),
        ]

        return custom + urls

    def valider_view(self, request, bon_id):

        bon = BonLivraison.objects.get(id=bon_id)

        bon.valider()

        self.message_user(request, "Bon de livraison validé ✔", messages.SUCCESS)

        return redirect("/admin/ventes/bonlivraison/")


#admin.site.register(BonLivraison, BonLivraisonAdmin)

# ===============================
# ADMIN LIGNE BON LIVRAISON
# ===============================

@admin.register(LigneBonLivraison)
class LigneBonLivraisonAdmin(admin.ModelAdmin):

    list_display = (
        "produit",
        "quantite",
        "prix_ht",
        "taux_tva",
    )
    
    
from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.shortcuts import redirect
from django.contrib import messages

from .models import AvoirClient, LigneAvoirClient


# ==========================
# INLINE
# ==========================
class LigneAvoirClientInline(admin.TabularInline):
    model = LigneAvoirClient
    extra = 1

    class Media:
        js = (
            "ventes/client_auto.js",
            "ventes/stock.js",
        )

    fields = ("produit", "quantite", "prix_ht", "taux_rem", "taux_tva")


# ==========================
# ADMIN AVOIR CLIENT
# ==========================
@admin.register(AvoirClient)
class AvoirClientAdmin(admin.ModelAdmin):

    inlines = [LigneAvoirClientInline]

    readonly_fields = ("numero", "total_ttc")

    list_display = (
        "numero",
        "client",
        "total_ttc_display",
        "bouton_pdf",
    )

    fields = (
        "numero",
        "date",
        "client",
        "mf_client",
        "adresse_client",
        "telephone_client",
        "email_client",
        "total_ttc",
    )

    search_fields = ("numero", "client__nom")

    # ==========================
    # SAVE RELATED (IMPORTANT)
    # ==========================
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.calculer_totaux()

    # ==========================
    # DISPLAY TOTAL
    # ==========================
    def total_ttc_display(self, obj):
        return f"{obj.total_ttc:.3f} TND"

    total_ttc_display.short_description = "Total TTC"

    # ==========================
    # PDF BUTTON
    # ==========================



    readonly_fields = ("numero", "total_ttc")

    # ==========================
    # PDF BUTTON
    # ==========================
    def bouton_pdf(self, obj):

        from django.urls import reverse
        from django.utils.html import format_html

        if not obj.id:
            return "-"

        url = reverse("avoir_pdf", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" target="_blank" '
            'style="background:#dc3545;color:white;padding:4px 8px;border-radius:4px;">PDF</a>',
            url
        )

    bouton_pdf.short_description = "PDF"

# ==========================
# ADMIN LIGNES
# ==========================
@admin.register(LigneAvoirClient)
class LigneAvoirClientAdmin(admin.ModelAdmin):

    list_display = ("produit", "quantite", "prix_ht")

