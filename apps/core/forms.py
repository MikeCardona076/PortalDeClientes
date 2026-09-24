from django import forms

from .models import PerfilUsuario


class PerfilForm(forms.ModelForm):
    correo = forms.EmailField(required=False, label="Correo de contacto")

    class Meta:
        model = PerfilUsuario
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.correos:
            self.fields["correo"].initial = self.instance.correos[0]

    def save(self, commit=True):
        perfil = super().save(commit=False)
        correo = (self.cleaned_data.get("correo") or "").strip()
        perfil.correos = [correo] if correo else []
        if commit:
            perfil.save()
            user = perfil.user
            user.email = correo
            user.save(update_fields=["email"])
        return perfil
