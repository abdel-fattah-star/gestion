from django.contrib import admin
from .models import Societe

from django.contrib import admin
from django.contrib.auth.models import User, Group

# cacher User et Group de l’admin
#admin.site.unregister(User)
#admin.site.unregister(Group)


from django.contrib import admin
from .models import Societe

@admin.register(Societe)
class SocieteAdmin(admin.ModelAdmin):


    list_display = (
        "nom",
        "matricule_fiscal",
        "pays",
        "ville",
        "telephone",
    )

    search_fields = (
        "nom",
        "matricule_fiscal",
    )
    def has_add_permission(self, request):
        # bloque ajout si déjà une société
        return not Societe.objects.exists()

from django.contrib import admin
from core.utils import get_societe

class ERPAdminSite(admin.AdminSite):

    def each_context(self, request):
        context = super().each_context(request)
        context['societe'] = get_societe()
        return context


admin_site = ERPAdminSite()