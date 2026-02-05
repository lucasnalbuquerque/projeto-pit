from django.db import models
from django.contrib.auth.models import User

# --- ENUMS ---
class StatusSolicitacao(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Pendente'
    EM_ANALISE = 'ANALISE', 'Em Análise'
    CONCLUIDA = 'CONCLUIDA', 'Concluída'
    CANCELADA = 'CANCELADA', 'Cancelada'

class TipoAtendimento(models.TextChoices):
    SINCRONO = 'SINCRONO', 'Síncrono'
    ASSINCRONO = 'ASSINCRONO', 'Assíncrono'

class Sexo(models.TextChoices):
    M = 'M', 'Masculino'
    F = 'F', 'Feminino'
    O = 'O', 'Outro'

# --- MODELS DE PERFIL ---

class Profissional(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    crm = models.CharField(max_length=20)
    cargo = models.CharField(max_length=100)
    instituicao = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.cargo})"

class Medica(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    crm = models.CharField(max_length=20)
    especialidade = models.CharField(max_length=100)

    def __str__(self):
        return f"Dra. {self.user.last_name} - {self.especialidade}"

# --- MODELO CENTRAL ---

class Solicitacao(models.Model):
    # Relacionamentos
    profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE, related_name='solicitacoes')
    medica_designada = models.ForeignKey(Medica, on_delete=models.SET_NULL, null=True, blank=True, related_name='atendimentos')
    
    # Controle e status
    status = models.CharField(max_length=20, choices=StatusSolicitacao.choices, default=StatusSolicitacao.PENDENTE)
    tipo_atendimento = models.CharField(max_length=20, choices=TipoAtendimento.choices)
    
    # timestamps importantes
    data_sol = models.DateTimeField(auto_now_add=True)

    # Ramificação UML: sincrono vs assincrono
    data_marcada = models.DateField(null=True, blank=True)
    horario_marcado = models.TimeField(null=True, blank=True)
    data_limite = models.DateField(null=True, blank=True)
    horario_limite = models.TimeField(null=True, blank=True)

    # Ramificação UML: geral vs especifico
    idade_pac = models.IntegerField()
    sexo_pac = models.CharField(max_length=1, choices=Sexo.choices)
    queixas = models.TextField()
    historico_med = models.TextField(blank=True, null=True)
    diagnostico_princ = models.TextField(blank=True, null=True)
    diagnostico_sec = models.TextField(blank=True, null=True)
    medicamentos = models.TextField(blank=True, null=True)
    exames_recentes = models.TextField(blank=True, null=True)
    duvida_clinica = models.TextField()

    # métodos de mudança de status
    def iniciar_analise(self):
        self.status = StatusSolicitacao.EM_ANALISE
        self.save()

    def finalizar(self):
        self.status = StatusSolicitacao.CONCLUIDA
        self.save()

    def cancelar(self):
        self.status = StatusSolicitacao.CANCELADA
        self.save()

    class Meta:
        verbose_name = "Solicitação"
        verbose_name_plural = "Solicitações"

    def __str__(self):
        return f"Solicitação #{self.id} - {self.profissional.user.last_name}"

# --- MODELO DE RESPOSTA ---

class Resposta(models.Model):
    solicitacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE, related_name='respostas')
    medica = models.ForeignKey(Medica, on_delete=models.CASCADE)
    conteudo = models.TextField()
    
    # anexo como atributo fraco
    anexo = models.FileField(upload_to='respostas_anexos/', null=True, blank=True)
    
    data_res = models.DateTimeField(auto_now_add=True)

    # métodos de salvamento
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.solicitacao.finalizar()

    def __str__(self):
        return f"Resposta de {self.medica} para Solicitacao #{self.solicitacao.id}"
    