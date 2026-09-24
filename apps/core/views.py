from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import PerfilForm
from .models import PerfilUsuario


@login_required
def perfil(request):
    perfil_obj, _ = PerfilUsuario.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=perfil_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos de contacto actualizados.")
            return redirect("core:perfil")
    else:
        form = PerfilForm(instance=perfil_obj)
    return render(
        request,
        "core/perfil.html",
        {"form": form, "perfil": perfil_obj},
    )


class CambioPasswordView(PasswordChangeView):
    template_name = "core/password_change_form.html"
    success_url = reverse_lazy("core:perfil")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["perfil"], _ = PerfilUsuario.objects.get_or_create(user=self.request.user)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        perfil_obj, _ = PerfilUsuario.objects.get_or_create(user=self.request.user)
        if perfil_obj.debe_cambiar_password:
            perfil_obj.debe_cambiar_password = False
            perfil_obj.save(update_fields=["debe_cambiar_password"])
        messages.success(self.request, "Contraseña actualizada.")
        return response
