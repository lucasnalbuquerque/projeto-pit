from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.core.mail import send_mail
from .models import Solicitacao, Resposta, Profissional, Medica, AnexoSolicitacao, AnexoResposta, LinkAcesso, HorarioFixoDisponivel
from datetime import datetime, timedelta, date
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import logging
import uuid 
import os
import pandas as pd
import threading

logger = logging.getLogger(__name__)


# LÓGICA DE ALERTA INTERNO POR E-MAIL (ASSÍNCRONA COM THREADS)
def _disparar_email_background(assunto, mensagem, destinatario):
    try:
        send_mail(
            subject=f"[HULW Alerta] {assunto}",
            message=mensagem,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail de alerta interno em background: {e}")

def enviar_alerta_desenvolvedor(assunto, mensagem):
    """
    Inicia uma nova Thread para enviar o e-mail de monitoramento sem bloquear a requisição HTTP principal.
    """
    destinatario = getattr(settings, 'DEVELOPER_EMAIL', None)
    if destinatario:
        # Cria e inicia a thread para rodar em paralelo ao ciclo de visualização do Django
        thread_email = threading.Thread(
            target=_disparar_email_background,
            args=(assunto, mensagem, destinatario)
        )
        thread_email.start()


# LÓGICA DE NOTIFICAÇÃO (E-MAIL VIA CSV)
def exportar_para_whatsapp_csv(solicitacao):
    caminho_csv = os.path.join(settings.BASE_DIR, 'log_notificacoes.csv')
    
    # Ordena por '-id' para sempre capturar o token mais recente gerado para o caso
    link_obj = LinkAcesso.objects.filter(solicitacao=solicitacao).order_by('-id').first()
    token = link_obj.token if link_obj else "token-nao-gerado"
    
    link_completo = f"{settings.SITE_URL}/acompanhar/{token}/"
    
    novos_dados = {
        'data_resposta': [timezone.now().strftime('%d/%m/%Y %H:%M')],
        'nome_solicitante': [solicitacao.profissional.nome_completo],
        'email': [solicitacao.profissional.email],
        'link_acesso': [link_completo],
        'status_envio': ['PENDENTE']
    }
    
    df_novo = pd.DataFrame(novos_dados)
    
    if os.path.exists(caminho_csv):
        df_antigo = pd.read_csv(caminho_csv)
        df_final = pd.concat([df_antigo, df_novo], ignore_index=True)
    else:
        df_final = df_novo
        
    df_final.to_csv(caminho_csv, index=False, encoding='utf-8-sig')


# LÓGICA DE TELECONSULTORIA SÍNCRONA (CSV)
def exportar_sincrono_csv(solicitacao):
    caminho_csv = os.path.join(settings.BASE_DIR, 'log_sincronos.csv')
    
    # Formata a data e hora agendadas para a teleconsultoria
    data_hora_str = ""
    if solicitacao.data_marcada and solicitacao.horario_marcado:
        data_hora_str = f"{solicitacao.data_marcada.strftime('%d/%m/%Y')} {solicitacao.horario_marcado.strftime('%H:%M')}"
    
    # Captura o token de acesso para redirecionar para a página da resposta/acompanhamento do caso
    link_obj = LinkAcesso.objects.filter(solicitacao=solicitacao).order_by('-id').first()
    token = link_obj.token if link_obj else "token-nao-gerado"
    link_resposta = f"{settings.SITE_URL}/acompanhar/{token}/"
    
    novos_dados = {
        'data_e_hora': [data_hora_str],
        'nome_solicitante': [solicitacao.profissional.nome_completo],
        'link_acesso': [link_resposta],
        'email': [solicitacao.profissional.email],
        'status_envio': ['PENDENTE']
    }
    
    df_novo = pd.DataFrame(novos_dados)
    
    if os.path.exists(caminho_csv):
        try:
            df_existente = pd.read_csv(caminho_csv)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        except Exception:
            df_final = df_novo
    else:
        df_final = df_novo
        
    df_final.to_csv(caminho_csv, index=False, encoding='utf-8-sig')


# LÓGICA DE CANCELAMENTO (CSV)
def exportar_cancelamento_csv(solicitacao, justificativa):
    caminho_csv = os.path.join(settings.BASE_DIR, 'log_cancelamentos.csv')
    
    novos_dados = {
        'data_cancelamento': [timezone.now().strftime('%d/%m/%Y %H:%M')],
        'nome_solicitante': [solicitacao.profissional.nome_completo],
        'email': [solicitacao.profissional.email],
        'motivo_cancelamento': [justificativa],
        'status_envio': ['PENDENTE']
    }
    
    df_novo = pd.DataFrame(novos_dados)
    
    if os.path.exists(caminho_csv):
        try:
            df_existente = pd.read_csv(caminho_csv)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        except Exception:
            df_final = df_novo
    else:
        df_final = df_novo
        
    df_final.to_csv(caminho_csv, index=False, encoding='utf-8-sig')


# LÓGICA DE REATIVAMENTO (CSV)
def exportar_reativamento_csv(solicitacao, novo_token):
    caminho_csv = os.path.join(settings.BASE_DIR, 'log_reativamentos.csv')
    link_completo = f"{settings.SITE_URL}/acompanhar/{novo_token}/"
    
    novos_dados = {
        'data': [timezone.now().strftime('%d/%m/%Y %H:%M')],
        'email': [solicitacao.profissional.email],
        'novo_link': [link_completo]
    }
    
    df_novo = pd.DataFrame(novos_dados)
    
    if os.path.exists(caminho_csv):
        try:
            df_existente = pd.read_csv(caminho_csv)
            df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        except Exception:
            df_final = df_novo
    else:
        df_final = df_novo
        
    df_final.to_csv(caminho_csv, index=False, encoding='utf-8-sig')


# FUNÇÃO DE VERIFICAÇÃO DE ACESSO
def is_medica(user):
    return user.is_authenticated and user.is_staff

# Reforço no backend da mesma regra aplicada no front-end (nova_solicitacao.html):
# e-mails de provedores públicos não são aceitos como e-mail profissional.
PROVEDORES_PUBLICOS = [
    'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com',
    'yahoo.com.br', 'uol.com.br', 'bol.com.br', 'icloud.com',
    'live.com', 'ig.com.br', 'terra.com.br'
]

def email_e_profissional(email):
    if not email or '@' not in email:
        return False
    dominio = email.split('@')[-1].strip().lower()
    return dominio not in PROVEDORES_PUBLICOS

# view: nova solicitação (Pública)
@never_cache
def nova_solicitacao(request):
    if request.method == 'POST':
        cpf_solicitante = request.POST.get('cpf')
        
        if cpf_solicitante:
            cpf_solicitante = ''.join(filter(str.isdigit, cpf_solicitante))

        text_solicitante = request.POST.get('nome_completo')
        email_solicitante = request.POST.get('email')
        telefone_solicitante = request.POST.get('telefone') 
        crm_solicitante = request.POST.get('crm')
        cargo_solicitante = request.POST.get('cargo')
        instituicao_solicitante = request.POST.get('instituicao')

        if not cpf_solicitante or not text_solicitante:
            return render(request, 'nova_solicitacao.html', {
                'erro': 'CPF e Nome Completo são obrigatórios para identificar o profissional.',
                'horarios_disponiveis': gerar_lista_disponibilidade()
            })

        if not email_e_profissional(email_solicitante):
            return render(request, 'nova_solicitacao.html', {
                'erro': 'Por favor, insira um e-mail institucional/profissional (não são aceitos e-mails de provedores públicos como Gmail, Hotmail, etc.).',
                'horarios_disponiveis': gerar_lista_disponibilidade()
            })

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
                nova_sol = Solicitacao.objects.create(**dados_base, idade_pac=0, sexo_pac='O', sexo_biologico_pac='O')
            else:
                nova_sol = Solicitacao.objects.create(
                    **dados_base,
                    idade_pac=request.POST.get('idade_pac') or 0,
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
        
        ocupados = Solicitacao.objects.filter(
            data_marcada=data_analise
        ).exclude(status='CANCELADA').values_list('horario_marcado', flat=True)
        
        ocupados_str = [h.strftime('%H:%M') for h in ocupados if h is not None]
        slots_da_grade = grade_fixa.filter(dia_semana=dia_semana_idx).order_by('horario')
        
        for slot in slots_da_grade:
            if slot.horario and slot.horario.strftime('%H:%M') not in ocupados_str:
                horarios_livres.append({
                    'data': data_analise,
                    'horario': slot.horario,
                    'id_formatado': f"{data_analise.strftime('%Y-%m-%d')}|{slot.horario.strftime('%H:%M')}"
                })
    return horarios_livres


# VIEWS RESTRITAS APENAS PARA A MÉDICA

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def fila_medica(request):
    solicitacoes = Solicitacao.objects.all().order_by('-data_sol')
    return render(request, 'fila_medica.html', {'solicitacoes': solicitacoes})

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
@never_cache
def detalhe_caso(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if solicitacao.status == 'PENDENTE':
        solicitacao.iniciar_analise()
        
        if hasattr(request.user, 'medica'):
            solicitacao.medica_designada = request.user.medica
        else:
            solicitacao.medica_designada = Medica.objects.first()
            
        solicitacao.save()
    
    link_obj = LinkAcesso.objects.filter(solicitacao=solicitacao).first()
    token = link_obj.token if link_obj else "token-nao-gerado"
    link_publico = f"{request.scheme}://{request.get_host()}/acompanhar/{token}/"
    
    # Log seguro: registra apenas o ID do caso, sem expor o link completo
    logger.info(f"Link de acesso gerado para o Caso #{solicitacao.id}")
    
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
        
        try:
            exportar_sincrono_csv(solicitacao)
            enviar_alerta_desenvolvedor(
                assunto=f"Link de Atendimento Adicionado - Caso #{solicitacao.id}",
                mensagem=f"A médica adicionou o link de acesso para o atendimento síncrono do caso #{solicitacao.id}."
            )
        except Exception as e:
            logger.error(f"Erro ao disparar e-mail de link síncrono para o caso #{solicitacao.id}: {e}")
            
        return redirect('detalhe_caso', sol_id=solicitacao.id)
    return render(request, 'agendar_sincrona.html', {'sol': solicitacao})

@login_required(login_url='login')
@user_passes_test(is_medica, login_url='login')
def responder_solicitacao(request, sol_id):
    solicitacao = get_object_or_404(Solicitacao, id=sol_id)
    if request.method == 'POST':
        texto_resposta = request.POST.get('resposta')
        
        if hasattr(request.user, 'medica'):
            medica_logada = request.user.medica
        else:
            medica_logada = Medica.objects.first()
        
        if not medica_logada:
            return render(request, 'detalhe_caso.html', {
                'sol': solicitacao,
                'erro': 'Seu usuário de testes não possui um perfil de Médica vinculado no painel de administração.'
            })
        
        with transaction.atomic():
            nova_resposta = Resposta.objects.create(solicitacao=solicitacao, medica=medica_logada, conteudo=texto_resposta)
            solicitacao.status = 'CONCLUIDA' 
            solicitacao.save()
            for f in request.FILES.getlist('anexos'):
                AnexoResposta.objects.create(resposta=nova_resposta, arquivo=f)
            
            try:
                exportar_para_whatsapp_csv(solicitacao)
                enviar_alerta_desenvolvedor(
                    assunto=f"Caso #{solicitacao.id} Respondido",
                    mensagem=f"Uma resposta foi inserida para o caso #{solicitacao.id} no sistema."
                )
            except Exception as e:
                logger.error(f"Erro ao exportar log WhatsApp ou notificar caso #{solicitacao.id}: {e}")
            
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
            exportar_cancelamento_csv(solicitacao, justificativa)
            enviar_alerta_desenvolvedor(
                assunto=f"Caso #{solicitacao.id} Cancelado",
                mensagem=f"O caso #{solicitacao.id} foi marcado como cancelado no painel administrativo."
            )
        except Exception as e:
            logger.error(f"Erro ao exportar log cancelamento para caso #{solicitacao.id}: {e}")
            
        return redirect('fila_medica')
    return render(request, 'cancelar_caso.html', {'sol': solicitacao})


# VIEWS PÚBLICAS (Acesso pelo solicitante)

@never_cache
def acompanhar_caso(request, token):
    link = get_object_or_404(LinkAcesso, token=token)
    agora = timezone.now()
    
    if link.data_criacao > (link.solicitacao.data_sol + timedelta(minutes=1)):
        horas_validade = 240
    else:
        horas_validade = 720
            
    data_limite_estimada = link.data_criacao + timedelta(hours=horas_validade)
    
    if data_limite_estimada <= agora:
        return render(request, 'link_expirado.html', {'link_obj': link}, status=403)
    
    segundos_restantes = 0
    if data_limite_estimada > agora:
        segundos_restantes = int((data_limite_estimada - agora).total_seconds())
    
    return render(request, 'acompanhar_caso.html', {
        'sol': link.solicitacao,
        'link_obj': link,
        'segundos_restantes': segundos_restantes  
    })

def renovar_acesso(request, token):
    if request.method != 'POST':
        return redirect('fila_medica')

    link_antigo = get_object_or_404(LinkAcesso, token=token)
    solicitacao = link_antigo.solicitacao

    # Evita reenvios repetidos em sequência buscando pelo registro mais atualizado do caso
    ultimo_link = LinkAcesso.objects.filter(solicitacao=solicitacao).order_by('-id').first()

    intervalo_minimo = timedelta(minutes=2)
    if ultimo_link and timezone.now() - ultimo_link.data_criacao < intervalo_minimo:
        return render(request, 'link_expirado.html', {
            'link_obj': link_antigo,
            'erro': 'Um link já foi gerado recentemente. Aguarde alguns minutos antes de solicitar novamente.'
        })

    # CRIAÇÃO DO NOVO LINK: Mantém o token antigo intacto e seguro no banco para exibir a tela de expirado,
    # e gera um novo registro limpo no banco que disparará a regra de 10 dias.
    novo_token = str(uuid.uuid4())
    LinkAcesso.objects.create(
        solicitacao=solicitacao,
        token=novo_token,
        data_criacao=timezone.now()
    )
    
    try:
        exportar_para_whatsapp_csv(solicitacao)
        enviar_alerta_desenvolvedor(
            assunto=f"Link Reativado - Caso #{solicitacao.id}",
            mensagem=f"Foi solicitada uma reativação/renovação de acesso para o caso #{solicitacao.id}."
        )
    except Exception as e:
        logger.error(f"Erro ao renovar via WhatsApp para caso #{solicitacao.id}: {e}")

    try:
        exportar_reativamento_csv(solicitacao, novo_token)
    except Exception as e:
        logger.error(f"Erro ao exportar log de reativamento para caso #{solicitacao.id}: {e}")
    
    return render(request, 'notificacao_enviada.html', {
        'email': solicitacao.profissional.email if solicitacao.profissional else "E-mail não cadastrado"
    })