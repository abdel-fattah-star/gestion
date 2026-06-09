from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from fournisseurs.models import Fournisseur
from produits.models import Produit
from django.db.models import Max


# =====================================================
# GENERATION NUMERO DEMANDE
# =====================================================

def generer_numero_demande():

    annee = now().year
    prefix = f"DEM-{annee}-"

    dernier = Demande.objects.filter(
        numero__startswith=prefix
    ).order_by("numero").last()

    if dernier:
        num = int(dernier.numero.split("-")[-1]) + 1
    else:
        num = 1

    return f"{prefix}{num:05d}"


# =====================================================
# DEMANDE DE PRIX
# =====================================================

class Demande(models.Model):

    STATUTS = (
        ("brouillon", "Brouillon"),
        ("envoye", "Envoyé"),
        ("accepte", "Accepté"),
        ("refuse", "Refusé"),
    )

    numero = models.CharField(max_length=30, unique=True, blank=True)

    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.PROTECT
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="brouillon"
    )

    date = models.DateField(default=timezone.now)

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    mf_fournisseur = models.CharField(max_length=50, blank=True)
    adresse_fournisseur = models.CharField(max_length=255, blank=True)
    telephone_fournisseur = models.CharField(max_length=20, blank=True)
    email_fournisseur = models.EmailField(blank=True)

    def __str__(self):
        return self.numero or "Demande"

    def save(self, *args, **kwargs):

        if not self.numero:
            self.numero = generer_numero_demande()

        super().save(*args, **kwargs)

    def calculer_totaux(self):

        total_ht = 0
        total_rem = 0
        base_tva = 0
        total_tva = 0
        total_ttc = 0

        for ligne in self.lignes.all():

            montant_ht = ligne.quantite * ligne.prix_ht
            montant_rem = montant_ht * (ligne.taux_rem or 0) / 100

            base = montant_ht - montant_rem
            tva = base * (ligne.taux_tva or 0) / 100

            total_ht += montant_ht
            total_rem += montant_rem
            base_tva += base
            total_tva += tva
            total_ttc += base + tva

        return {
            "total_ht": total_ht,
            "total_rem": total_rem,
            "base_tva": base_tva,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
        }


class LigneDemande(models.Model):

    demande = models.ForeignKey(
        Demande,
        on_delete=models.CASCADE,
        related_name="lignes"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT
    )

    quantite = models.DecimalField(max_digits=10, decimal_places=3)

    prix_ht = models.DecimalField("Prix Achat",max_digits=10, decimal_places=3)

    taux_rem = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    taux_tva = models.DecimalField(max_digits=4, decimal_places=2)

    def montant_ht(self):
        return self.quantite * self.prix_ht


# =====================================================
# BON RECEPTION
# =====================================================

class BonReception(models.Model):

    numero = models.CharField(max_length=20, unique=True, blank=True)

    date = models.DateField(default=timezone.now)

    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.PROTECT
    )

    statut = models.CharField(
        max_length=20,
        choices=[
            ("brouillon", "Brouillon"),
            ("validee", "Validée"),
        ],
        default="brouillon"
    )

    mf_fournisseur = models.CharField(max_length=30, blank=True)
    adresse_fournisseur = models.CharField(max_length=200, blank=True)
    telephone_fournisseur = models.CharField(max_length=30, blank=True)
    email_fournisseur = models.CharField(max_length=100, blank=True)

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return f"BR {self.numero}"

    def calculer_totaux(self):
        total_ht = 0
        total_rem = 0
        base_tva = 0
        total_tva = 0
        total_ttc = 0

        for ligne in self.lignes.all():
            montant_ht = ligne.quantite * ligne.prix_ht
            remise = montant_ht * (ligne.taux_rem or 0) / 100
            base = montant_ht - remise
            tva = base * (ligne.taux_tva or 0) / 100
            ttc = base + tva

            total_ht += montant_ht
            total_rem += remise
            base_tva += base
            total_tva += tva
            total_ttc += ttc

        # MAJ automatique des champs
        self.total_ht = total_ht
        self.total_rem = total_rem
        self.base_tva = base_tva
        self.total_tva = total_tva
        self.total_ttc = total_ttc

        return {
            "total_ht": total_ht,
            "total_rem": total_rem,
            "base_tva": base_tva,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
        }

    def save(self, *args, **kwargs):
        # Mise à jour infos client
        if self.client:
            self.mf_client = self.client.matricule_fiscal
            self.adresse_client = self.client.adresse
            self.telephone_client = self.client.telephone
            self.email_client = self.client.email

        # Génération numéro si vide
        if not self.numero:
            self.numero = generer_numero_bonlivraison()

        super().save(*args, **kwargs)

        # recalcul total après sauvegarde (pour nouvelles lignes)
        self.calculer_totaux()
        super().save(update_fields=["total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"])




    def save(self, *args, **kwargs):

        if not self.numero:

            dernier = BonReception.objects.aggregate(Max("numero"))

            if dernier["numero__max"]:
                self.numero = str(int(dernier["numero__max"]) + 1)
            else:
                self.numero = "1"

        super().save(*args, **kwargs)


class LigneBonReception(models.Model):

    bon_reception = models.ForeignKey(
        BonReception,
        related_name="lignes",
        on_delete=models.CASCADE
    )

    produit = models.ForeignKey("produits.Produit", on_delete=models.CASCADE)
    quantite = models.DecimalField(max_digits=10, decimal_places=3)
    prix_ht = models.DecimalField(max_digits=10, decimal_places=3)
    taux_rem = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=19)

    def montant_ht(self):
        return self.quantite * self.prix_ht

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # recalcul automatique du bon après modification de la ligne
        self.bon_reception.calculer_totaux()
        self.bon_reception.save(update_fields=["total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"])

    def delete(self, *args, **kwargs):
        bon = self.bon_reception
        super().delete(*args, **kwargs)
        bon.calculer_totaux()
        bon.save(update_fields=["total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"])



# =====================================================
# FACTURE ACHAT
# =====================================================

def generer_numero_facture_achat():

    annee = now().year
    prefix = f"FAC-A-{annee}-"

    derniere = FactureAchat.objects.filter(
        numero__startswith=prefix
    ).order_by("numero").last()

    if derniere:
        num = int(derniere.numero.split("-")[-1]) + 1
    else:
        num = 1

    return f"{prefix}{num:05d}"


class FactureAchat(models.Model):

    STATUTS = (
        ("brouillon", "Brouillon"),
        ("validee", "Validée"),
        ("payee", "Payée"),
    )

    numero = models.CharField(max_length=30, unique=True, blank=True)

    fournisseur = models.ForeignKey(
        Fournisseur,
        on_delete=models.PROTECT
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="brouillon"
    )

    date = models.DateField(default=timezone.now)

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    mf_fournisseur = models.CharField(max_length=50, blank=True)
    adresse_fournisseur = models.CharField(max_length=255, blank=True)
    telephone_fournisseur = models.CharField(max_length=20, blank=True)
    email_fournisseur = models.EmailField(blank=True)

    def __str__(self):
        return self.numero or "Facture Achat"

#------- calcul totaux

    def calculer_totaux(self):

        total_ht = 0
        total_rem = 0
        base_tva = 0
        total_tva = 0
        total_ttc = 0

        for ligne in self.lignes.all():

            montant_ht = ligne.quantite * ligne.prix_ht
            rem = montant_ht * (ligne.taux_rem or 0) / 100
            base = montant_ht - rem
            tva = base * (ligne.taux_tva or 0) / 100

            total_ht += montant_ht
            total_rem += rem
            base_tva += base
            total_tva += tva
            total_ttc += base + tva 

        return {
            "total_ht": total_ht,
            "total_rem": total_rem,
            "base_tva": base_tva,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
        }


    # 🔥 CALCUL QUI MET A JOUR LES CHAMPS
    def calculer_totaux(self):
        total_ht = 0
        total_rem = 0
        total_tva = 0
        base_tva = 0

        for ligne in self.lignes.all():
            montant_ht = ligne.quantite * ligne.prix_ht
            montant_rem = montant_ht * ligne.taux_rem / 100
            montant_base_tva = montant_ht - montant_rem
            montant_tva = montant_base_tva * ligne.taux_tva / 100

            total_ht += montant_ht
            total_rem += montant_rem
            total_tva += montant_tva
            base_tva += montant_base_tva

        total_ttc = base_tva + total_tva + 1

        # mise à jour des champs
        self.total_ht = total_ht
        self.total_rem = total_rem
        self.total_tva = total_tva
        self.base_tva = base_tva
        self.total_ttc = total_ttc
        

        return {   # 🔥 RAJOUTE ÇA
            "total_ht": total_ht,
            "total_rem":total_rem,
            "base_tva":base_tva,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
        }

    def save(self, *args, **kwargs):
        if self.fournisseur:
            self.mf_fournisseur = self.fournisseur.matricule_fiscal
            self.adresse_fournisseur = self.fournisseur.adresse
            self.telephone_fournisseur = self.fournisseur.telephone
            self.email_fournisseur = self.fournisseur.email

#-----------------------

    def save(self, *args, **kwargs):

        if not self.numero:
            self.numero = generer_numero_facture_achat()

        super().save(*args, **kwargs)


class LigneFactureAchat(models.Model):

    facture = models.ForeignKey(
        FactureAchat,
        on_delete=models.CASCADE,
        related_name="lignes"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.PROTECT
    )

    quantite = models.DecimalField(max_digits=10, decimal_places=3)

    prix_ht = models.DecimalField("Prix Achat", max_digits=10, decimal_places=3)

    taux_rem = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    taux_tva = models.DecimalField(max_digits=4, decimal_places=2)

    def montant_ht(self):
        return self.quantite * self.prix_ht 

    # ✅ BIEN DANS LA CLASSE
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.facture.calculer_totaux()
        self.facture.save(update_fields=["total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"])

    def delete(self, *args, **kwargs):
        facture = self.facture
        super().delete(*args, **kwargs)

        facture.calculer_totaux()
        facture.save(update_fields=["total_ht", "taotal_rem", "base_tva", "total_tva", "total_ttc"])

#-------- Avoir fournisseur

from django.db import models
from django.utils.timezone import now


def generer_numero_avoirfournisseur():
    annee = now().year
    prefix = f"AVF-{annee}-"

    derniere = AvoirFournisseur.objects.filter(numero__startswith=prefix).order_by("numero").last()

    if derniere:
        num = int(derniere.numero.split("-")[-1]) + 1
    else:
        num = 1

    return f"{prefix}{num:05d}"


class AvoirFournisseur(models.Model):

    numero = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField(default=now)

    fournisseur = models.ForeignKey(
        "fournisseurs.Fournisseur",
        on_delete=models.PROTECT
    )

    statut = models.CharField(
        max_length=20,
        choices=[
            ("brouillon", "Brouillon"),
            ("validee", "Validée"),
        ],
        default="brouillon"
    )

    mf_fournisseur = models.CharField(max_length=30, blank=True)
    adresse_fournisseur = models.CharField(max_length=200, blank=True)
    telephone_fournisseur = models.CharField(max_length=30, blank=True)
    email_fournisseur = models.CharField(max_length=100, blank=True)

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return f"AVF {self.numero}"

    def calculer_totaux(self):
        total_ht = total_rem = base_tva = total_tva = total_ttc = 0

        for ligne in self.lignes.all():
            montant_ht = ligne.quantite * ligne.prix_ht
            remise = montant_ht * (ligne.taux_rem or 0) / 100
            base = montant_ht - remise
            tva = base * (ligne.taux_tva or 0) / 100
            ttc = base + tva

            total_ht += montant_ht
            total_rem += remise
            base_tva += base
            total_tva += tva
            total_ttc += ttc

        self.total_ht = total_ht
        self.total_rem = total_rem
        self.base_tva = base_tva
        self.total_tva = total_tva
        self.total_ttc = total_ttc

        return {
            "total_ht": total_ht,
            "total_rem": total_rem,
            "base_tva": base_tva,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
        }

    def save(self, *args, **kwargs):

        if self.fournisseur:
            self.mf_fournisseur = self.fournisseur.matricule_fiscal
            self.adresse_fournisseur = self.fournisseur.adresse
            self.telephone_fournisseur = self.fournisseur.telephone
            self.email_fournisseur = self.fournisseur.email

        if not self.numero:
            self.numero = generer_numero_avoirfournisseur()

        super().save(*args, **kwargs)

        self.calculer_totaux()
        super().save(update_fields=[
            "total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"
        ])


# ===============================
# LIGNES
# ===============================
class LigneAvoirFournisseur(models.Model):

    avoir_fournisseur = models.ForeignKey(
        AvoirFournisseur,
        related_name="lignes",
        on_delete=models.CASCADE
    )

    produit = models.ForeignKey("produits.Produit", on_delete=models.CASCADE)
    quantite = models.DecimalField(max_digits=10, decimal_places=3)
    prix_ht = models.DecimalField(max_digits=10, decimal_places=3)
    taux_rem = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=19)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.avoir_fournisseur.calculer_totaux()
        self.avoir_fournisseur.save(update_fields=[
            "total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"
        ])

    def delete(self, *args, **kwargs):
        avoir = self.avoir_fournisseur
        super().delete(*args, **kwargs)

        avoir.calculer_totaux()
        avoir.save(update_fields=[
            "total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"
        ])


#-------- Fin


