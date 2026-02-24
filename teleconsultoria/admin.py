from django.contrib import admin
from .models import Profissional, Medica, Solicitacao, Resposta, HorarioFixoDisponivel
from datetime import time
from django import forms
from django.core.exceptions import ValidationError

# Registra os modelos básicos
admin.site.register(Profissional)
admin.site.register(Medica)
admin.site.register(Resposta)

class HorarioFixoForm(forms.ModelForm):
    HORARIOS_PERMITIDOS = [
        (time(h, m), f"{h:02d}:{m:02d}") 
        for h in range(8, 18) 
        for m in (0, 30)
    ]
    
    horario = forms.ChoiceField(choices=HORARIOS_PERMITIDOS, label="Horário")
    
    operacao = forms.ChoiceField(
        choices=[('add', 'Adicionar'), ('del', 'Remover')],
        widget=forms.RadioSelect,
        initial='add',
        label="O que deseja fazer?"
    )

    class Meta:
        model = HorarioFixoDisponivel
        fields = ['dia_semana', 'horario', 'operacao']

    # Remove a validação de "já existe" para permitir a remoção
    def validate_unique(self):
        pass

@admin.register(HorarioFixoDisponivel)
class HorarioFixoAdmin(admin.ModelAdmin):
    form = HorarioFixoForm
    list_display = ('get_dia_semana_display', 'horario')
    list_filter = ('dia_semana',)
    ordering = ('dia_semana', 'horario')

    def save_model(self, request, obj, form, change):
        operacao = form.cleaned_data.get('operacao')
        
        existente = HorarioFixoDisponivel.objects.filter(
            dia_semana=obj.dia_semana, 
            horario=obj.horario
        )

        if operacao == 'del':
            existente.delete()
            self.message_user(request, "Horário removido com sucesso.")
        else:
            if not existente.exists():
                obj.save()
                self.message_user(request, "Horário adicionado com sucesso.")
            else:
                self.message_user(request, "Este horário já estava na grade.", level='WARNING')

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        last_obj = HorarioFixoDisponivel.objects.order_by('-id').first()
        if last_obj:
            initial['dia_semana'] = last_obj.dia_semana
            initial['horario'] = last_obj.horario
        return initial

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context.update({'show_save_and_continue': False})
        return super().render_change_form(request, context, add, change, form_url, obj)