from django.contrib import admin
from .models import ReglementClient, ReglementFournisseur,MouvementCompte
from django.urls import reverse
from django.utils.html import format_html


@admin.register(ReglementClient)
class ReglementClientAdmin(admin.ModelAdmin):

    list_display = ("numero", "date", "client", "montant", "mode_paiement", "imprimer_quittance")
    search_fields = ("numero", "client__nom")
    exclude = ("numero",)


    def imprimer_quittance(self, obj):
        url = reverse("quittance_client_pdf", args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank">Imprimer</a>',
            url
        )

    imprimer_quittance.short_description = "Quittance"



@admin.register(ReglementFournisseur)
class ReglementFournisseurAdmin(admin.ModelAdmin):

    list_display = ("numero", "date", "fournisseur", "montant", "mode_paiement", "imprimer_quittance")
    search_fields = ("numero", "fournisseur__nom")
    exclude = ("numero",)
    
    def imprimer_quittance(self, obj):
        url = reverse("quittance_fournisseur_pdf", args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank">Imprimer</a>',
            url
        )

    imprimer_quittance.short_description="quittance"


#----- mvtcpte

@admin.register(MouvementCompte)
class MouvementCompteAdmin(admin.ModelAdmin):

    list_display = (
        "date",
        "type_mouvement",
        "compte",
        "montant"
    )

    list_filter = ("type_mouvement", "compte")

    search_fields = ("reference",)
