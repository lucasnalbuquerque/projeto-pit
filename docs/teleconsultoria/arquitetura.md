# Arquitetura de Referência – Teleconsultoria

Objetivo: propor uma arquitetura usando apenas (ou prioritariamente) as ferramentas listadas no README do projeto.

## Cenário MVP (mínimo viável)

- Comunicação e vídeo: Microsoft Teams
- Agendamento: Outlook (calendário institucional) + formulário (Microsoft Forms/Power Apps)
- Repositório de documentos: SharePoint (bibliotecas com permissões por equipe)
- Fluxos/automação: Power Automate (notificações, criação de reuniões, registro em lista)
- Registro mínimo da consulta: Lista SharePoint (metadados: paciente pseudonimizado/ID interno, profissional, data, status, link da reunião)
- Testes de APIs: Postman; Monitoramento de chamadas HTTP: Fiddler (ambiente de dev)

Vantagens: rápido para iniciar, baixo custo adicional, governança Microsoft 365.

## Cenário Estendido (integrações e governança)

- Diretório e acesso: Microsoft Entra ID (Azure AD)
- Prontuário/Registros clínicos: integração via APIs do sistema hospitalar (sem dados sensíveis no repositório do projeto)
- Banco de dados estruturado: Dataverse (Power Platform) ou Azure SQL (quando necessário)
- Segredos/credenciais: Azure Key Vault
- Observabilidade: Azure Monitor / Application Insights (para apps customizados)
- Integração com Power BI: dashboards operacionais (volumes, tempos de espera, satisfação)

## Controles de Segurança e LGPD (camada transversal)

- Menor privilégio (permissões por equipe e função)
- Criptografia em trânsito (HTTPS/Teams) e em repouso (SharePoint/Dataverse)
- Registro de consentimento (Forms/Power Apps) vinculado ao atendimento
- Trilha de auditoria (versionamento no SharePoint, logs do Power Automate, auditoria M365)
- Segregação de ambientes: desenvolvimento, homologação, produção na Power Platform

## Fluxo alto nível

1. Solicitação de teleconsulta (Forms/Power Apps) -> grava em lista SharePoint/Dataverse
2. Automação cria reunião Teams e envia convites (Power Automate)
3. Realização da teleconsulta no Teams
4. Registro do atendimento e anexos com metadados (SharePoint/Dataverse)
5. Relatórios operacionais (Power BI)

## Princípios

- Evitar dados sensíveis fora dos sistemas clínicos oficiais
- Identificadores pseudonimizados nos artefatos operacionais
- Automatizar notificações, agendamentos e registros mínimos
- Auditar acessos e mudanças
