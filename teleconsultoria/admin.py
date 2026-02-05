from django.contrib import admin
from .models import Profissional, Medica, Solicitacao, Resposta

# Registra os modelos básicos
admin.site.register(Profissional)
admin.site.register(Medica)
admin.site.register(Resposta)

# Customização para a Solicitação aparecer de forma organizada
@admin.register(Solicitacao)
class SolicitacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'profissional', 'status', 'tipo_atendimento', 'data_sol')
    list_filter = ('status', 'tipo_atendimento')
    search_fields = ('profissional__user__first_name', 'idade_pac')
    
    # Adiciona a action de cancelamento
    actions = ['cancelar_solicitacoes']

    @admin.action(description="Cancelar solicitações selecionadas")
    def cancelar_solicitacoes(self, request, queryset):
        for solicitacao in queryset:
            solicitacao.cancelar()