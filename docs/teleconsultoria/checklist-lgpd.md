# Checklist LGPD e Segurança – Teleconsultoria

Use esta lista para validar o MVP e a versão estendida.

## Governança

- Classificar dados (pessoais, sensíveis) e minimizar coleta

## Acesso e Identidade

- Usar contas institucionais (Entra ID/Azure AD)
- Princípio do menor privilégio (perfis por papel)
- MFA habilitado para todos os envolvidos

## Dados e Armazenamento

- Registro mínimo em SharePoint/Dataverse com IDs pseudonimizados
- Não armazenar dados clínicos detalhados fora do prontuário oficial
- Retenção e descarte definidos (políticas M365/Dataverse)

## Segurança de Aplicações

- Segredos em Azure Key Vault (ou equivalente) – nunca em repositório
- TLS/HTTPS em todas as integrações
- Auditoria e logs habilitados (M365, Power Automate, Dataverse)

## Direitos dos Titulares

- Processo para atender solicitações (acesso, correção, eliminação)
- Registro de consentimento e revogação

## Incidentes

- Plano de resposta a incidentes (contatos, prazos, comunicação)
- Teste periódico do plano (simulado)
