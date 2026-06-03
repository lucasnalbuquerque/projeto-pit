import uuid
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

# --- ENUMS ---
class StatusSolicitacao(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente'
    EM_ANALISE = 'ANALISE', 'Em Análise'
    AGENDADO = 'AGENDADO', 'Reunião Agendada'
    CONCLUIDA = 'CONCLUIDA', 'Concluída'
    CANCELADA = 'CANCELADA', 'Cancelada'
    AUSENTE = 'AUSENTE', 'Ausente'

class TipoAtendimento(models.TextChoices):
    SINCRONO = 'SINCRONO', 'Síncrono'
    ASSINCRONO = 'ASSINCRONO', 'Assíncrono'

class Sexo(models.TextChoices):
    M = 'M', 'Masculino'
    F = 'F', 'Feminino'
    O = 'O', 'Outro'

class DiaSemana(models.IntegerChoices):
    SEGUNDA = 0, 'Segunda-feira'
    TERCA = 1, 'Terça-feira'
    QUARTA = 2, 'Quarta-feira'
    QUINTA = 3, 'Quinta-feira'
    SEXTA = 4, 'Sexta-feira'
    SABADO = 5, 'Sábado'
    DOMINGO = 6, 'Domingo'

# --- MODELS DE CONFIGURAÇÃO ---

class HorarioFixoDisponivel(models.Model):
    dia_semana = models.IntegerField(choices=DiaSemana.choices)
    horario = models.TimeField()
    ativo = models.BooleanField(default=True, help_text="Define se este horário da grade semanal está ativo")

    class Meta:
        verbose_name = "Horário Fixo da Semana"
        verbose_name_plural = "Grade de Horários Fixos"
        ordering = ['dia_semana', 'horario']
        unique_together = ['dia_semana', 'horario']

    def __str__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f"{self.get_dia_semana_display()} às {self.horario.strftime('%H:%M')} - {status}"

# --- MODELS DE PERFIL ---

class Profissional(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    
    cpf = models.CharField(max_length=11, unique=True) 
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField()
    telefone = models.CharField(max_length=15, help_text="WhatsApp com DDD", blank=True, null=True)
    crm = models.CharField(max_length=20, blank=True, null=True)
    cargo = models.CharField(max_length=100)
    instituicao = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nome_completo} - {self.cargo}"

class Medica(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='medica')
    nome_completo = models.CharField(max_length=255, default="Médica Teleconsultora")
    crm = models.CharField(max_length=20)
    especialidade = models.CharField(max_length=100)

    def __str__(self):
        return f"Dra. {self.nome_completo} - {self.especialidade}"

# --- MODELO CENTRAL ---

class Solicitacao(models.Model):
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE, related_name='solicitacoes')
    medica_designada = models.ForeignKey(Medica, on_delete=models.SET_NULL, null=True, blank=True, related_name='atendimentos')
    
    status = models.CharField(max_length=20, choices=StatusSolicitacao.choices, default=StatusSolicitacao.PENDENTE)
    tipo_atendimento = models.CharField(max_length=20, choices=TipoAtendimento.choices)
    data_sol = models.DateTimeField(auto_now_add=True)

    data_marcada = models.DateField(null=True, blank=True)
    horario_marcado = models.TimeField(null=True, blank=True)
    duracao_estimada = models.PositiveIntegerField(null=True, blank=True, help_text="Duração em minutos")
    link_teams = models.URLField(max_length=500, null=True, blank=True)
    justificativa_cancelamento = models.TextField(null=True, blank=True)
    
    data_limite = models.DateField(null=True, blank=True)
    horario_limite = models.TimeField(null=True, blank=True)

    # Campos do Paciente
    idade_pac = models.IntegerField(null=True, blank=True)
    sexo_pac = models.CharField(max_length=2, choices=Sexo.choices, null=True, blank=True)
    sexo_biologico_pac = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], null=True, blank=True)
    queixas = models.TextField(null=True, blank=True)
    historico_med = models.TextField(blank=True, null=True)
    diagnostico_princ = models.TextField(blank=True, null=True)
    diagnostico_sec = models.TextField(blank=True, null=True)
    medicamentos = models.TextField(blank=True, null=True)
    exames_recentes = models.TextField(blank=True, null=True)
    duvida_clinica = models.TextField()

    # Adicionando o campo de token para o detalhe_caso funcionar
    token_acesso = models.UUIDField(default=uuid.uuid4, editable=False)

    # métodos de mudança de status
    def iniciar_analise(self):
        self.status = StatusSolicitacao.EM_ANALISE
        self.save()

    def agendar_reuniao(self, data, horario, link):
        self.data_marcada = data
        self.horario_marcado = horario
        self.link_teams = link
        self.tipo_atendimento = TipoAtendimento.SINCRONO
        self.status = StatusSolicitacao.AGENDADO
        self.save()

    def finalizar(self):
        self.status = StatusSolicitacao.CONCLUIDA
        self.save()

    def registrar_ausencia(self):
        self.status = StatusSolicitacao.AUSENTE
        self.save()

    def cancelar(self, justificativa=""):
        self.status = StatusSolicitacao.CANCELADA
        self.justificativa_cancelamento = justificativa
        self.save()

    class Meta:
        verbose_name = "Solicitação"
        verbose_name_plural = "Solicitações"

    def __str__(self):
        return f"Solicitação #{self.id} - {self.profissional.user.last_name if self.profissional.user else self.profissional.nome_completo}"

# --- MODELO DE RESPOSTA ---

class Resposta(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='respostas')
    medica = models.ForeignKey(Medica, on_delete=models.CASCADE)
    conteudo = models.TextField()
    
    data_res = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.solicitacao.finalizar()

    def __str__(self):
        return f"Resposta de {self.medica} para Solicitacao #{self.solicitacao.id}"

# --- MODELOS DE ANEXOS ---

class AnexoSolicitacao(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to='solicitacoes_anexos/')
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anexo da Solicitacao #{self.solicitacao.id}"

class AnexoResposta(models.Model):
    resposta = models.ForeignKey(Resposta, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(upload_to='respostas_anexos/')
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anexo da Resposta #{self.id}"

# --- MODELO DE LINK MÁGICO ---

class LinkAcesso(models.Model):
    solicitacao = models.OneToOneField(Solicitacao, on_delete=models.CASCADE, related_name='link_magico')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    expirado = models.BooleanField(default=False)

    def is_valido(self):
        prazo = self.data_criacao + timezone.timedelta(days=7)
        return timezone.now() < prazo and not self.expirado

    def __str__(self):
        return f"Token para Solicitacao #{self.solicitacao.id}"