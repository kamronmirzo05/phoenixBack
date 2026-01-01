from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    path('click/prepare/', views.click_prepare_view, name='click_prepare'),
    path('click/complete/', views.click_complete_view, name='click_complete'),
    path('click/callback/', views.ClickPaymentView.as_view(), name='click_callback'),
    path('card-token/request/', views.request_card_token_view, name='request_card_token'),
    path('card-token/verify/', views.verify_card_token_view, name='verify_card_token'),
    path('card-token/pay/', views.pay_with_card_token_view, name='pay_with_card_token'),
    path('', include(router.urls)),
]