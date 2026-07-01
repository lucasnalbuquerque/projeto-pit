from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView  # adicionar este import
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='nova_solicitacao'), name='home'),  # adicionar esta linha

    # --- TELA DE LOGIN E LOGOUT NATIVOS ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # --- ROTAS EXISTENTES ---
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)