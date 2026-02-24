from django.shortcuts import render, redirect, get_object_or_404
from .models import Solicitacao, Resposta, Profissional, Medica, AnexoSolicitacao, AnexoResposta, LinkAcesso, HorarioFixoDisponivel
from datetime import datetime, timedelta, date
from django.db import transaction
from django.utils import timezone

# view: nova solicitação
def nova_solicitacao(request):
    if request.method == 'POST':
        profissional_teste = Profissional.objects.first()
        tipo_caso = request.POST.get('tipo_caso')
        modalidade = request.POST.get('tipo_atendimento', 'ASSINCRONO')
        # Prazo limite padrão para resposta
        prazo_limite = timezone.now() + timedelta(days=7)
        
        data_m = None
        hora_m = None
        
        if modalidade == 'SINCRONO':
            agenda_string = request.POST.get('agenda_id') # Formato: YYYY-MM-DD|HH:MM
            if agenda_string:
                try:
                    dt_str, hr_str = agenda_string.split('|')
                    data_m = datetime.strptime(dt_str, '%Y-%m-%d').date()
                    hora_m = datetime.strptime(hr_str, '%H:%M').time()
                    
                    # Validação de Segurança: impede agendamento para o mesmo dia no POST
                    if data_m <= date.today():
                        return render(request, 'nova_solicitacao.html', {
                            'erro': 'Agendamentos só podem ser realizados a partir de amanhã.',
                            'horarios_disponiveis': gerar_lista_disponibilidade()
                        })

                    # Verifica se o horário ainda está vago
                    exists = Solicitacao.objects.filter(
                        data_marcada=data_m, 
                        horario_marcado=hora_m
                    ).exclude(status='CANCELADA').exists()
                    
                    if exists:
                        return render(request, 'nova_solicitacao.html', {
                            'erro': 'Este horário foi ocupado recentemente. Por favor, selecione outro.',
                            'horarios_disponiveis': gerar_lista_disponibilidade()
                        })
                except (ValueError, IndexError):
                    pass

        with transaction.atomic():
            dados_base = {
                'profissional': profissional_teste,
                'tipo_atendimento': modalidade,
                'data_marcada': data_m,
                'horario_marcado': hora_m,
                'duracao_estimada': 30 if modalidade == 'SINCRONO' else None,
                'duvida_clinica': request.POST.get('duvida_clinica'),
                'data_limite': prazo_limite.date(),
                'horario_limite': prazo_limite.time(),
                'status': 'PENDENTE'
            }
            
            if tipo_caso == 'GERAL':
                nova_sol = Solicitacao.objects.create(**dados_base, idade_pac=0, sexo_pac='O')
            else:
                nova_sol = Solicitacao.objects.create(
                    **dados_base,
                    idade_pac=request.POST.get('idade_pac') or 0,
                    sexo_pac=request.POST.get('sexo_pac'),
                    diagnostico_princ=request.POST.get('diagnostico_princ'),
                    diagnostico_sec=request.POST.get('diagnostico_sec'),
                    queixas=request.POST.get('queixas_especificas'),
                    historico_med=request.POST.get('historico_med'),
                    medicamentos=request.POST.get('medicamentos'),
                    exames_recentes=request.POST.get('exames_recentes')
                )
            
            LinkAcesso.objects.create(solicitacao=nova_sol)
            arquivos = request.FILES.getlist('anexos')
            for f in arquivos:
                AnexoSolicitacao.objects.create(solicitacao=nova_sol, arquivo=f)
            
        return redirect('fila_medica')
    
    return render(request, 'nova_solicitacao.html', {
        'horarios_disponiveis': gerar_lista_disponibilidade()
    })

def gerar_lista_disponibilidade():
    """Calcula horários livres para os próximos 14 dias, ignorando o dia de hoje"""
    horarios_livres = []
    hoje = date.today()
    grade_fixa = HorarioFixoDisponivel.objects.filter(ativo=True)
    
    # Inicia em 1 para garantir que o agendamento seja no mínimo para amanhã
    for i in range(1, 15):
        data_analise = hoje + timedelta(days=i)
        dia_semana_idx = data_analise.weekday() 
        
        ocupados = Solicitacao.objects.filter(
            data_marcada=data_analise
        ).exclude(status='CANCELADA').values_list('horario_marcado', flat=True)
        
        slots_da_grade = grade_fixa.filter(dia_semana=dia_semana_idx).order_by('horario')
        
        for slot in slots_da_grade:
            if slot.horario not in ocupados:
                horarios_livres.append({
                    'data': data_analise,
                    'horario': slot.horario,
                    'id_formatado': f"{data_analise.strftime('%Y-%m-%d')}|{slot.horario.strftime('%H:%M')}"
                })
    return horarios_livres

# Outras views (fila_medica, detalhe_caso, etc) permanecem iguais...
def fila_medica(request):
    solicitacoes = Solicitacao.objects.all().order_by('-data_sol')
    return render(request, 'fila_medica.html', {'solicitacoes': solicitacoes})

def detalhe_caso(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if solicitacao.status == 'PENDENTE':
        solicitacao.iniciar_analise()
    return render(request, 'detalhe_caso.html', {'sol': solicitacao})

def responder_solicitacao(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if request.method == 'POST':
        texto_resposta = request.POST.get('resposta')
        medica_teste = Medica.objects.first()
        nova_resposta = Resposta.objects.create(solicitacao=solicitacao, medica=medica_teste, conteudo=texto_resposta)
        for f in request.FILES.getlist('anexos'):
            AnexoResposta.objects.create(resposta=nova_resposta, arquivo=f)
        return redirect('fila_medica')
    return render(request, 'responder.html', {'sol': solicitacao})

def agendar_sincrona(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if request.method == 'POST':
        link = request.POST.get('link_teams')
        solicitacao.agendar_reuniao(data=solicitacao.data_marcada, horario=solicitacao.horario_marcado, link=link)
        return redirect('detalhe_caso', sol_id=solicitacao.id)
    return render(request, 'agendar_sincrona.html', {'sol': solicitacao})

def acompanhar_caso(request, token):
    link = get_object_or_404(LinkAcesso, token=token)
    if not link.is_valido():
        return render(request, 'link_expirado.html', status=403)
    return render(request, 'acompanhar_caso.html', {'sol': link.solicitacao})