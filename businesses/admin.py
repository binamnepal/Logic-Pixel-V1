from django import forms
from django.contrib import admin
from .models import Business, StaffProfile, scope_queryset


class BusinessForm(forms.ModelForm):
    access_token = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False),
                                   help_text="Leave blank to keep the current token.")

    class Meta:
        model = Business
        exclude = ("access_token_enc",)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.cleaned_data.get("access_token"):
            obj.set_token(self.cleaned_data["access_token"])
        if commit:
            obj.save()
        return obj


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    form = BusinessForm
    list_display = ("name", "business_type", "phone_number_id", "active")

    def get_queryset(self, request):
        return scope_queryset(super().get_queryset(request), request.user, path="pk")


admin.site.register(StaffProfile)
