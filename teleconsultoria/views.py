from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Solicitacao, Resposta, Profissional, Medica, AnexoSolicitacao, AnexoResposta, LinkAcesso, HorarioFixoDisponivel
from datetime import datetime, timedelta, date
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import uuid 
import os
import pandas as pd  # Adicionado para a lógica do WhatsApp

# --- LÓGICA DE NOTIFICAÇÃO (WHATSAPP VIA EXCEL) ---
def exportar_para_whatsapp_excel(solicitacao):

    caminho_excel = os.path.join(settings.BASE_DIR, 'log_notificacoes.xlsx')
    link_obj = LinkAcesso.objects.filter(solicitacao=solicitacao).first()
    token = link_obj.token if link_obj else "token-nao-gerado"
    
    # Monta o link que o profissional usará para ver a resposta
    link_completo = f"{settings.SITE_URL}/acompanhar/{token}/"
    
    novos_dados = {
        'data_resposta': [timezone.now().strftime('%d/%m/%Y %H:%M')],
        'nome_solicitante': [solicitacao.profissional.nome_completo],
        'whatsapp': [solicitacao.profissional.telefone],
        'link_acesso': [link_completo],
        'status_envio': ['PENDENTE']
    }
    
    df_novo = pd.DataFrame(novos_dados)
    
    if os.path.exists(caminho_excel):
        df_antigo = pd.read_excel(caminho_excel)
        df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
    else:
        df_final = df_novo
        
    df_final.to_excel(caminho_excel, index=False)


# --- NOVA LÓGICA DE CANCELAMENTO (EXCEL) ---
def exportar_cancelamento_excel(solicitacao, justificativa):
    caminho_excel = os.path.join(settings.BASE_DIR, 'log_cancelamentos.xlsx')
    
    novos_dados = {
        'data_cancelamento': [timezone.now().strftime('%d/%m/%Y %H:%M')],
        'nome_solicitante': [solicitacao.profissional.nome_completo],
        'whatsapp': [solicitacao.profissional.telefone],
        'motivo_cancelamento': [justificativa],
        'status_envio': ['PENDENTE']
    }
    
    df_novo = pd.DataFrame(novos_dados)
    
    if os.path.exists(caminho_excel):
        try:
            df_existente = pd.read_excel(caminho_excel)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        except Exception:
            df_final = df_novo
    else:
        df_final = df_novo
        
    df_final.to_excel(caminho_excel, index=False)


# --- NOVA LÓGICA DE REATIVAMENTO (EXCEL) ---
def exportar_reativamento_excel(solicitacao, novo_token):
    caminho_excel = os.path.join(settings.BASE_DIR, 'log_reativamentos.xlsx')
    link_completo = f"{settings.SITE_URL}/acompanhar/{novo_token}/"
    
    novos_dados = {
        'data': [timezone.now().strftime('%d/%m/%Y %H:%M')],
        'whatsapp': [solicitacao.profissional.telefone],
        'novo_link': [link_completo]
    }
    
    df_novo = pd.DataFrame(novos_dados)
    
    if os.path.exists(caminho_excel):
        try:
            df_existente = pd.read_excel(caminho_excel)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        except Exception:
            df_final = df_novo
    else:
        df_final = df_novo
        
    df_final.to_excel(caminho_excel, index=False)


# --- FUNÇÃO DE VERIFICAÇÃO DE ACESSO ---
# Permite o acesso de qualquer usuário criado por você (Staff) no painel administrativo
def is_medica(user):
    return user.is_authenticated and user.is_staff

# view: nova solicitação (Pública, qualquer um pode acessar)
def nova_solicitacao(request):
    if request.method == 'POST':
        cpf_solicitante = request.POST.get('cpf')
        text_solicitante = request.POST.get('nome_completo')
        email_solicitante = request.POST.get('email')
        telefone_solicitante = request.POST.get('telefone') # CAPTURA DO WHATSAPP
        crm_solicitante = request.POST.get('crm')
        cargo_solicitante = request.POST.get('cargo')
        instituicao_solicitante = request.POST.get('instituicao')

        if not cpf_solicitante or not text_solicitante:
            return render(request, 'nova_solicitacao.html', {
                'erro': 'CPF e Nome Completo são obrigatórios para identificar o profissional.',
                'horarios_disponiveis': gerar_lista_disponibilidade()
            })

        # BUSCA PELO CPF E ATUALIZA TODOS OS DADOS COM OS NOVOS VALORES DO FORMULÁRIO
        profissional_solicitante, created = Profissional.objects.update_or_create(
            cpf=cpf_solicitante,
            defaults={
                'nome_completo': text_solicitante,
                'email': email_solicitante,
                'telefone': telefone_solicitante,
                'crm': crm_solicitante,
                'cargo': cargo_solicitante,
                'instituicao': instituicao_solicitante
            }
        )

        tipo_caso = request.POST.get('tipo_caso')
        modalidade = request.POST.get('tipo_atendimento', 'ASSINCRONO')
        prazo_limite = timezone.now() + timedelta(days=7)
        
        data_m = None
        hora_m = None
        
        if modalidade == 'SINCRONO':
            agenda_string = request.POST.get('agenda_id') 
            if agenda_string:
                try:
                    dt_str, hr_str = agenda_string.split('|')
                    data_m = datetime.strptime(dt_str, '%Y-%m-%d').date()
                    hora_m = datetime.strptime(hr_str, '%H:%M').time()

                    if data_m <= date.today():
                        return render(request, 'nova_solicitacao.html', {
                            'erro': 'Agendamentos só podem ser realizados a partir de amanhã.',
                            'horarios_disponiveis': gerar_lista_disponibilidade()
                        })

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
                'profissional': profissional_solicitante,
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
                # Se for geral, define valores padrão ou nulos para o sexo biológico se o model permitir
                nova_sol = Solicitacao.objects.create(**dados_base, idade_pac=0, sexo_pac='O', sexo_biologico_pac='O')
            else:
                nova_sol = Solicitacao.objects.create(
                    **dados_base,
                    id_pac=request.POST.get('idade_pac') or 0,
                    sexo_pac=request.POST.get('sexo_pac'),
                    sexo_biologico_pac=request.POST.get('sexo_biologico_pac'), 
                    diagnostico_princ=request.POST.get('diagnostico_princ'),
                    diagnostico_sec=request.POST.get('diagnostico_sec'),
                    queixas=request.POST.get('queixas_especificas'), 
                    historico_med=request.POST.get('historico_med'),
                    medicamentos=request.POST.get('medicamentos'),
                    exames_recentes=request.POST.get('exames_recentes')
                )
            
            link_obj = LinkAcesso.objects.create(solicitacao=nova_sol)
            
            # Mudado de 'anexos' para 'arquivos_anexos' para sincronizar com o HTML
            arquivos = request.FILES.getlist('arquivos_anexos')
            for f in arquivos:
                AnexoSolicitacao.objects.create(solicitacao=nova_sol, arquivo=f)
            
        return render(request, 'sucesso.html', {'token': link_obj.token})
    
    return render(request, 'nova_solicitacao.html', {
        'horarios_disponiveis': gerar_lista_disponibilidade()
    })

def gerar_lista_disponibilidade(): 
    horarios_livres = []
    hoje = date.today()
    grade_fixa = HorarioFixoDisponivel.objects.filter(ativo=True)
    for i in range(1, 15):
        data_analise = hoje + timedelta(days=i)
        dia_semana_idx = data_analise.weekday() 
        
        # CORREÇÃO: Formata a lista de horários ocupados como strings para comparação à prova de falhas
        ocupados = Solicitacao.objects.filter(
            data_marcada=data_analise
        ).exclude(status='CANCELADA').values_list('horario_marcado', flat=True)
        
        ocupados_str = [h.strftime('%H:%M') for h in ocupados if h is not None]
        
        slots_da_grade = grade_fixa.filter(dia_semana=dia_semana_idx).order_by('horario')
        
        for slot in slots_da_grade:
            # CORREÇÃO: Compara a string gerada pelo slot com a lista de strings ocupadas
            if slot.horario and slot.horario.strftime('%H:%M') not in ocupados_str:
                horarios_livres.append({
                    'data': data_analise,
                    'horario': slot.horario,
                    'id_formatado': f"{data_analise.strftime('%Y-%m-%d')}|{slot.horario.strftime('%H:%M')}"
                })
    return horarios_livres


# --- VIEWS RESTRITAS APENAS PARA A MÉDICA ---

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def fila_medica(request):
    solicitacoes = Solicitacao.objects.all().order_by('-data_sol')
    return render(request, 'fila_medica.html', {'solicitacoes': solicitacoes})

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def detalhe_caso(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if solicitacao.status == 'PENDENTE':
        solicitacao.iniciar_analise()
        
        # CORREÇÃO CONTRA QUEDAS: Verifica se o usuário tem o perfil médica, senão usa a primeira cadastrada
        if hasattr(request.user, 'medica'):
            solicitacao.medica_designada = request.user.medica
        else:
            solicitacao.medica_designada = Medica.objects.first()
            
        solicitacao.save()
    
    link_obj = LinkAcesso.objects.filter(solicitacao=solicitacao).first()
    token = link_obj.token if link_obj else "token-nao-gerado"
    link_publico = f"{request.scheme}://{request.get_host()}/acompanhar/{token}/"
    
    print("\n" + "="*50)
    print(f"LINK DE ACESSO PÚBLICO (Caso #{solicitacao.id}): {link_publico}")
    print("="*50 + "\n")
    
    return render(request, 'detalhe_caso.html', {'sol': solicitacao})

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def agendar_sincrona(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if request.method == 'POST':
        link = request.POST.get('link_teams')
        solicitacao.link_teams = link
        solicitacao.status = 'AGENDADO'
        solicitacao.save()
        return redirect('detalhe_caso', sol_id=solicitacao.id)
    return render(request, 'agendar_sincrona.html', {'sol': solicitacao})

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def responder_solicitacao(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if request.method == 'POST':
        texto_resposta = request.POST.get('resposta')
        
        # CORREÇÃO CONTRA QUEDAS: Se o Admin puro responder, o sistema usa a primeira médica do banco como autora
        if hasattr(request.user, 'medica'):
            medica_logada = request.user.medica
        else:
            medica_logada = Medica.objects.first()
        
        with transaction.atomic():
            nova_resposta = Resposta.objects.create(solicitacao=solicitacao, medica=medica_logada, conteudo=texto_resposta)
            solicitacao.status = 'CONCLUIDA' 
            solicitacao.save()
            for f in request.FILES.getlist('anexos'):
                AnexoResposta.objects.create(resposta=nova_resposta, arquivo=f)
            
            try:
                # DISPARO PARA O WHATSAPP (EXCEL)
                exportar_para_whatsapp_excel(solicitacao)
            except Exception as e:
                print(f"Erro ao exportar log WhatsApp: {e}")
            
        return redirect('fila_medica')
    return render(request, 'responder.html', {'sol': solicitacao})

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def concluir_sincrona(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if solicitacao.tipo_atendimento == 'SINCRONO':
        solicitacao.status = 'CONCLUIDA'
        solicitacao.save()
    return redirect('fila_medica')

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def registrar_ausencia(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    solicitacao.registrar_ausencia()
    return redirect('fila_medica')

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def cancelar_solicitacao(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if request.method == 'POST':
        justificativa = request.POST.get('justificativa')
        
        if justificativa == 'OUTRO':
            texto_livre = request.POST.get('justificativa_detalhada')
            
            if texto_livre and texto_livre.strip():
                justificativa = texto_livre.strip()
            else:
                justificativa = 'Motivo não especificado.'
                
        solicitacao.cancelar(justificativa)
        
        try:
            exportar_cancelamento_excel(solicitacao, justificativa)
        except Exception as e:
            print(f"Erro ao exportar log cancelamento: {e}")
            
        return redirect('fila_medica')
    return render(request, 'cancelar_caso.html', {'sol': solicitacao})


# --- VIEWS PÚBLICAS (Acesso pelo solicitante) ---

def acompanhar_caso(request, token):
    link = get_object_or_404(LinkAcesso, token=token)
    if not link.is_valido():
        return render(request, 'link_expirado.html', {'link_obj': link}, status=403)
    
    agora = timezone.now()
    segundos_restantes = 0
    
    if link.data_criacao:
        horas_validade = 240
        data_limite_estimada = link.data_criacao + timedelta(hours=horas_validade)
        
        if data_limite_estimada > agora:
            segundos_restantes = int((data_limite_estimada - agora).total_seconds())
    
    return render(request, 'acompanhar_caso.html', {
        'sol': link.solicitacao,
        'link_obj': link,
        'segundos_restantes': segundos_restantes  
    })

def renovar_acesso(request, token):
    link_antigo = get_object_or_404(LinkAcesso, token=token)
    solicitacao = link_antigo.solicitacao
    
    novo_token = str(uuid.uuid4())
    link_antigo.token = novo_token
    link_antigo.data_criacao = timezone.now()
    link_antigo.save()
    
    try:
        exportar_para_whatsapp_excel(solicitacao)
    except Exception as e:
        print(f"Erro ao renovar via WhatsApp: {e}")

    try:
        # SALVA O LOG DE REATIVAMENTO NO EXCEL (data, whatsapp, novo_link)
        exportar_reativamento_excel(solicitacao, novo_token)
    except Exception as e:
        print(f"Erro ao exportar log de reativamento: {e}")
    
    return render(request, 'notificacao_enviada.html', {
        'email': solicitacao.profissional.telefone if solicitacao.profissional else "Telefone não cadastrado"
    })