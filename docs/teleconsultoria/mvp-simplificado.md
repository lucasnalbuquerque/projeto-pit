# MVP Simplificado – Teleconsultoria (sem desenvolvimento)

Objetivo: colocar um fluxo básico de teleconsultas no ar em 1–2 dias usando apenas Microsoft 365.

Ferramentas

- Microsoft Forms (solicitação + consentimento)
- SharePoint (lista de solicitações e registro mínimo)
- Power Automate (automação de agendamento e notificações)
- Outlook/Teams (reuniões)
- Power BI Desktop (opcional: métricas locais)

Passo a passo

1) SharePoint – criar lista “SolicitacoesTele” com colunas:
   - Protocolo (Texto) – ID pseudonimizado
   - Solicitante (Texto ou Pessoa)
   - Especialidade (Escolha)
   - Preferência de data/horário (Data/Hora)
   - Status (Escolha: Novo, Em triagem, Agendado, Concluído, Cancelado)
   - LinkReuniao (Hiperlink)
2) Forms – criar formulário “Solicitação de Teleconsulta”
   - Campos mínimos para preencher a lista
   - Checkbox de consentimento
3) Power Automate – fluxo “Agendar Teleconsulta”
   - Gatilho: nova resposta no Forms
   - Ações: criar item na lista SharePoint; criar reunião Teams/Outlook; atualizar item com LinkReuniao; enviar e-mails ao solicitante/equipe
4) Triagem – visualizar a lista no SharePoint e ajustar Status/atribuição
5) Consulta – realizar no Teams com link do item
6) Registro – atualizar Status para Concluído e anexar documentos operacionais na biblioteca do time (sem dados clínicos detalhados)

RBAC (rápido)

- SharePoint: grupos Tele-Administradores (Controle total), Tele-Triagem (Editar “SolicitacoesTele”), Tele-Médicos (Ler/Editar LinkReuniao e Status), Tele-Visualizadores (Leitura)
- Forms: limitar respostas ao domínio; notificações ao grupo de triagem
- Power Automate: conexões com conta de serviço

LGPD (essencial)

- Coletar o mínimo necessário e pseudonimizar (Protocolo)
- Consentimento no Forms; registro do aceite
- Sem dados clínicos detalhados no SharePoint; usar apenas sistemas clínicos oficiais

Definição de pronto (DoD)

- Lista SharePoint criada e acessível por papéis
- Formulário respondendo cria item e envia e-mail
- Fluxo cria reunião no Teams e grava LinkReuniao
- Triagem/Consulta/Conclusão percorrendo os status
