from django.urls import path
from . import views

urlpatterns = [
    path('nova/', views.nova_solicitacao, name='nova_solicitacao'),
    path('acompanhar/<uuid:token>/', views.acompanhar_caso, name='acompanhar_caso'),
    
    path('renovar-acesso/<uuid:token>/', views.renovar_acesso, name='renovar_acesso'),
    
    path('fila/', views.fila_medica, name='fila_medica'),
    path('detalhe/<int:sol_id>/', views.detalhe_caso, name='detalhe_caso'),
    path('responder/<int:sol_id>/', views.responder_solicitacao, name='responder_solicitacao'),

  
    path('agendar-sincrona/<int:sol_id>/', views.agendar_sincrona, name='agendar_sincrona'),
    
    path('ausencia/<int:sol_id>/', views.registrar_ausencia, name='registrar_ausencia'),
    path('cancelar/<int:sol_id>/', views.cancelar_solicitacao, name='cancelar_solicitacao'),
    path('concluir-sincrona/<int:sol_id>/', views.concluir_sincrona, name='concluir_sincrona'),
]