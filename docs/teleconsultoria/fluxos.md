# Fluxos Operacionais – Teleconsultoria

Abaixo, os principais fluxos usando as ferramentas do README.

## Agendamento

1. Solicitante preenche Microsoft Forms ou App no Power Apps
2. Power Automate valida disponibilidade e grava solicitação em SharePoint/Dataverse
3. Power Automate cria evento no Outlook/Teams e envia e-mails ao paciente e equipe

## Triagem

1. Lista de solicitações é revisada por profissional designado (SharePoint/Power Apps)
2. Power Automate envia checklist pré-consulta (consentimento, termos) via e-mail

## Consulta (Teams)

1. Reunião ocorre no Microsoft Teams
2. Materiais/arquivos são anexados em biblioteca SharePoint da equipe

## Registro e Encerramento

1. Registro mínimo do atendimento (metadados) em SharePoint/Dataverse
2. Power Automate notifica responsáveis e atualiza status
3. (Opcional) Integra com prontuário via API do hospital (Postman para testar, depois automatizar)

## Follow-up e Métricas

1. Envio de feedback/satisfação (Forms) e registro em SharePoint/Dataverse
2. Power BI lê dados operacionais para dashboards

## Regras e Políticas

- Não registrar dados sensíveis fora dos sistemas clínicos (Dados sensíveis não serão enviados ao repositório github)
- Usar IDs pseudonimizados nas listas e relatórios
- Restringir acesso por função (RBAC - Role based acess control) no SharePoint e Power Platform
