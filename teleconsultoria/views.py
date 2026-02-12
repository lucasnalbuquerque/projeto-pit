from django.shortcuts import render, redirect, get_object_or_404
from .models import Solicitacao, Resposta, Profissional, Medica, AnexoSolicitacao, AnexoResposta, LinkAcesso
from datetime import datetime, timedelta

# view: nova solicitação
def nova_solicitacao(request):
    if request.method == 'POST':
        profissional_teste = Profissional.objects.first()
        tipo_caso = request.POST.get('tipo_caso')
        prazo_limite = datetime.now() + timedelta(days=7)
        
        if tipo_caso == 'GERAL':
            nova_sol = Solicitacao.objects.create(
                profissional=profissional_teste,
                tipo_atendimento='ASSINCRONO',
                duvida_clinica=request.POST.get('duvida_clinica'),
                idade_pac=0,
                sexo_pac='O',
                data_limite=prazo_limite.date(),
                horario_limite=prazo_limite.time(),
                status='PENDENTE'
            )
        else:
            nova_sol = Solicitacao.objects.create(
                profissional=profissional_teste,
                tipo_atendimento='ASSINCRONO',
                idade_pac=request.POST.get('idade_pac') or 0,
                sexo_pac=request.POST.get('sexo_pac'),
                diagnostico_princ=request.POST.get('diagnostico_princ'),
                diagnostico_sec=request.POST.get('diagnostico_sec'),
                queixas=request.POST.get('queixas_especificas'),
                historico_med=request.POST.get('historico_med'),
                medicamentos=request.POST.get('medicamentos'),
                exames_recentes=request.POST.get('exames_recentes'),
                duvida_clinica=request.POST.get('duvida_clinica'),
                data_limite=prazo_limite.date(),
                horario_limite=prazo_limite.time(),
                status='PENDENTE'
            )
            
        # gera o link mágico automaticamente para a nova solicitação
        link_obj = LinkAcesso.objects.create(solicitacao=nova_sol)

        # --- LOG PARA TESTE (Exibe o link no terminal) ---
        url_acompanhamento = request.build_absolute_uri(f'/acompanhar/{link_obj.token}/')
        print("\n" + "="*60)
        print(f"NOVO CASO CRIADO: Solicitação #{nova_sol.id}")
        print(f"LINK MÁGICO DE ACESSO: {url_acompanhamento}")
        print("="*60 + "\n")
            
        arquivos = request.FILES.getlist('anexos')
        for f in arquivos:
            AnexoSolicitacao.objects.create(solicitacao=nova_sol, arquivo=f)
            
        return redirect('fila_medica')
    
    return render(request, 'nova_solicitacao.html')

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
        
        nova_resposta = Resposta.objects.create(
            solicitacao=solicitacao, 
            medica=medica_teste, 
            conteudo=texto_resposta
        )
        
        arquivos = request.FILES.getlist('anexos')
        for f in arquivos:
            AnexoResposta.objects.create(resposta=nova_resposta, arquivo=f)
        
        return redirect('fila_medica')

    return render(request, 'responder.html', {'sol': solicitacao})

# view protegida por token para o solicitante acompanhar o caso
def acompanhar_caso(request, token):
    link = get_object_or_404(LinkAcesso, token=token)
    
    # bloqueia acesso se o token estiver expirado ou invalidado
    if not link.is_valido():
        return render(request, 'link_expirado.html', status=403)
    
    return render(request, 'acompanhar_caso.html', {'sol': link.solicitacao})