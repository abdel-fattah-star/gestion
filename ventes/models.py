from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from clients.models import Client
from produits.models import Produit
from django.db.models import Max

#------ Devis et Ligne devis

def generer_numero_devis():
    annee = now().year
    prefix = f"DEV-{annee}-"
    dernier = Devis.objects.filter(numero__startswith=prefix).order_by("numero").last()

    if dernier:
        num = int(dernier.numero.split("-")[-1]) + 1
    else:
        num = 1

    return f"{prefix}{num:05d}"


class Devis(models.Model):

    STATUTS = (
        ("brouillon", "Brouillon"),
        ("envoye", "Envoyé"),
        ("accepte", "Accepté"),
        ("refuse", "Refusé"),
    )

    numero = models.CharField(max_length=30, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    statut = models.CharField(max_length=20, choices=STATUTS, default="brouillon")
    date = models.DateField(default=timezone.now)

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    mf_client = models.CharField(max_length=50, blank=True)
    adresse_client = models.CharField(max_length=255, blank=True)
    telephone_client = models.CharField(max_length=20, blank=True)
    email_client = models.EmailField(blank=True)

    def __str__(self):
        return self.numero or "Devis"


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

    def total_ttc(self, obj):

        totaux = obj.calculer_totaux()

        if totaux and totaux["total_ttc"] is not None:
            return f"{totaux['total_ttc']:.3f} TND"

        return "0.000 TND"

    total_ttc.short_description = "Total TTC"


class LigneDevis(models.Model):

    devis = models.ForeignKey(
        Devis,
        on_delete=models.CASCADE,
        related_name="lignes"
    )

    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)

    taux_rem = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    quantite = models.DecimalField(max_digits=10, decimal_places=3)
    prix_ht = models.DecimalField(max_digits=10, decimal_places=3)
    taux_tva = models.DecimalField(max_digits=4, decimal_places=2)

    def montant_ht(self):
        return self.quantite * self.prix_ht





#----------------------------
from django.db import models
from django.utils.timezone import now

def generer_numero_bonlivraison():
    annee = now().year
    prefix = f"BON.N°-{annee}-"
    derniere = BonLivraison.objects.filter(numero__startswith=prefix).order_by("numero").last()

    if derniere:
        num = int(derniere.numero.split("-")[-1]) + 1
    else:
        num = 1

    return f"{prefix}{num:05d}"


class BonLivraison(models.Model):

    numero = models.CharField(max_length=20, unique=True)
    date = models.DateField(default=timezone.now)

    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE)

    mf_client = models.CharField(max_length=30, blank=True)
    adresse_client = models.CharField(max_length=200, blank=True)
    telephone_client = models.CharField(max_length=30, blank=True)
    email_client = models.CharField(max_length=100, blank=True)
    facture = models.ForeignKey(
        "Facture",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    statut = models.CharField(
        max_length=20,
        choices=[
            ("brouillon","Brouillon"),
            ("validee","Validée"),
        ],
        default="brouillon"
    )

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return f"BL {self.numero}"

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


#-------- Lignes bon de livraison
class LigneBonLivraison(models.Model):

    bon_livraison = models.ForeignKey(
        BonLivraison,
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
        self.bon_livraison.calculer_totaux()
        self.bon_livraison.save(update_fields=["total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"])

    def delete(self, *args, **kwargs):
        bon = self.bon_livraison
        super().delete(*args, **kwargs)
        bon.calculer_totaux()
        bon.save(update_fields=["total_ht", "total_rem", "base_tva", "total_tva", "total_ttc"])

#---------------------------- Bon d'avoir client

from django.db import models
from django.utils.timezone import now


def generer_numero_avoirclient():
    annee = now().year
    prefix = f"AVOIR-{annee}-"

    derniere = AvoirClient.objects.filter(numero__startswith=prefix).order_by("numero").last()

    if derniere:
        num = int(derniere.numero.split("-")[-1]) + 1
    else:
        num = 1

    return f"{prefix}{num:05d}"


class AvoirClient(models.Model):

    numero = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField(default=now)

    client = models.ForeignKey("clients.Client", on_delete=models.CASCADE)

    mf_client = models.CharField(max_length=30, blank=True)
    adresse_client = models.CharField(max_length=200, blank=True)
    telephone_client = models.CharField(max_length=30, blank=True)
    email_client = models.CharField(max_length=100, blank=True)

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    def __str__(self):
        return f"AV {self.numero}"

    # ==========================
    # CALCUL TOTAL
    # ==========================
    def calculer_totaux(self):

        total_ht = 0
        total_rem = 0
        base_tva = 0
        total_tva = 0
        total_ttc = 0

        for ligne in self.lignes.all():

            montant_ht = ligne.quantite * ligne.prix_ht
            rem = montant_ht * (getattr(ligne, "taux_rem", 0) or 0) / 100
            base = montant_ht - rem
            tva = base * (getattr(ligne, "taux_tva", 0) or 0) / 100
            ttc = base + tva

            total_ht += montant_ht
            total_rem += rem
            base_tva += base
            total_tva += tva
            total_ttc += ttc

        return {
            "total_ht": total_ht,
            "total_rem": total_rem,
            "base_tva": base_tva,
            "total_tva": total_tva,
            "total_ttc": total_ttc,
        }

    # ==========================
    # SAVE PROPRE
    # ==========================
    def save(self, *args, **kwargs):

        if self.client:
            self.mf_client = self.client.matricule_fiscal
            self.adresse_client = self.client.adresse
            self.telephone_client = self.client.telephone
            self.email_client = self.client.email

        if not self.numero:
            self.numero = generer_numero_avoirclient()

        super().save(*args, **kwargs)

        # recalcul SAFE
        totaux = self.calculer_totaux()

        self.total_ht = totaux["total_ht"]
        self.total_rem = totaux["total_rem"]
        self.base_tva = totaux["base_tva"]
        self.total_tva = totaux["total_tva"]
        self.total_ttc = totaux["total_ttc"]

        super().save(update_fields=[
            "total_ht",
            "total_rem",
            "base_tva",
            "total_tva",
            "total_ttc"
        ])


# ==========================
# LIGNES AVOIR CLIENT
# ==========================
class LigneAvoirClient(models.Model):

    avoir_client = models.ForeignKey(
        AvoirClient,
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

        # recalcul propre (comme bon livraison)
        totaux = self.avoir_client.calculer_totaux()

        self.avoir_client.total_ht = totaux["total_ht"]
        self.avoir_client.total_rem = totaux["total_rem"]
        self.avoir_client.base_tva = totaux["base_tva"]
        self.avoir_client.total_tva = totaux["total_tva"]
        self.avoir_client.total_ttc = totaux["total_ttc"]
        self.avoir_client.save(update_fields=[
            "total_ht",
            "total_rem",
            "base_tva",
            "total_tva",
            "total_ttc"
        ])

#--------------------------- Fin

def generer_numero_facture():
    annee = now().year
    prefix = f"FAC-{annee}-"
    derniere = Facture.objects.filter(numero__startswith=prefix).order_by("numero").last()

    if derniere:
        num = int(derniere.numero.split("-")[-1]) + 1
    else:
        num = 1

    return f"{prefix}{num:05d}"


class Facture(models.Model):

    STATUTS = (
        ("brouillon", "Brouillon"),
        ("validee", "Validée"),
        ("payee", "Payée"),
    )

    numero = models.CharField(max_length=30, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    statut = models.CharField(max_length=20, choices=STATUTS, default="brouillon")
    date = models.DateField(default=timezone.now)

    total_ht = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_rem = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    base_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_tva = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_ttc = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    
    mf_client = models.CharField(max_length=50, blank=True)
    adresse_client = models.CharField(max_length=255, blank=True)
    telephone_client = models.CharField(max_length=20, blank=True)
    email_client = models.EmailField(blank=True)

    def __str__(self):
        return self.numero or "Facture"

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
    def valider(self):
        if self.statut != "validee":
            self.statut = "validee"
            self.save(update_fields=["statut"])

    def save(self, *args, **kwargs):
        if self.client:
            self.mf_client = self.client.matricule_fiscal
            self.adresse_client = self.client.adresse
            self.telephone_client = self.client.telephone
            self.email_client = self.client.email

        # Génération numéro si vide
        if not self.numero:
            super().save(*args, **kwargs)
            self.numero = generer_numero_facture()

        super().save(*args, **kwargs)


class LigneFacture(models.Model):
    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name="lignes"
    )
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT)
    taux_rem = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    quantite = models.DecimalField(max_digits=10, decimal_places=3)
    prix_ht = models.DecimalField(max_digits=10, decimal_places=3)
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
