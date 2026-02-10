from django.urls import path
from . import views

urlpatterns = [
    path('nova/', views.nova_solicitacao, name='nova_solicitacao'),
    path('fila/', views.fila_medica, name='fila_medica'),
    path('detalhe/<int:sol_id>/', views.detalhe_caso, name='detalhe_caso'),
    path('responder/<int:sol_id>/', views.responder_solicitacao, name='responder_solicitacao'),
]