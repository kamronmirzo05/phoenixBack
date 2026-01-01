from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from django.http import JsonResponse
from django.views import View
import logging

from .models import Transaction
from .serializers import TransactionSerializer, CreateTransactionSerializer
from .services import ClickPaymentService

logger = logging.getLogger(__name__)


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing transactions"""

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter transactions by user"""
        if self.request.user.is_superuser:
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Set the user when creating a transaction"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def prepare_payment(self, request, pk=None):
        """Prepare payment for transaction"""
        transaction = self.get_object()
        service = ClickPaymentService.get_service_for_service_type(transaction.service_type)
        result = service.prepare_payment(transaction)
        logger.info(f"Prepare payment result: {result}")
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def check_status(self, request, pk=None):
        """Check payment status"""
        transaction = self.get_object()
        
        # Return the transaction status directly
        result = {
            'id': transaction.id,
            'status': transaction.status,
            'amount': transaction.amount,
            'service_type': transaction.service_type,
            'created_at': transaction.created_at,
            'completed_at': transaction.completed_at,
            'click_trans_id': transaction.click_trans_id,
            'click_paydoc_id': transaction.click_paydoc_id,
            'error_code': transaction.error_code,
            'error_note': transaction.error_note,
        }
        
        logger.info(f"Check status result: {result}")
        return Response(result)
    
    @action(detail=True, methods=['get'])
    def get_payment_url(self, request, pk=None):
        """Get payment URL for redirecting user to Click payment page"""
        transaction = self.get_object()
        service = ClickPaymentService.get_service_for_service_type(transaction.service_type)
        
        # Frontend dan return URL olish (agar berilgan bo'lsa)
        return_url = request.query_params.get('return_url', None)
        
        payment_url = service.get_payment_url(transaction, return_url=return_url)
        
        logger.info(f"Payment URL generated for transaction {transaction.id}: {payment_url}")
        return Response({'payment_url': payment_url})


@api_view(['POST'])
@permission_classes([AllowAny])
def click_prepare_view(request):
    """Handle Click prepare requests"""
    logger.info(f"Click prepare request received: {request.data}")
    # service_id asosida to'g'ri xizmat turini aniqlash
    service_id = request.data.get('service_id')
    service = ClickPaymentService(service_id=service_id)
    result = service.handle_prepare(request.data)
    logger.info(f"Click prepare result: {result}")
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def click_complete_view(request):
    """Handle Click complete requests"""
    logger.info(f"Click complete request received: {request.data}")
    # service_id asosida to'g'ri xizmat turini aniqlash
    service_id = request.data.get('service_id')
    service = ClickPaymentService(service_id=service_id)
    result = service.handle_complete(request.data)
    logger.info(f"Click complete result: {result}")
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_card_token_view(request):
    """Request card token for payment"""
    try:
        card_number = request.data.get('card_number')
        expire_date = request.data.get('expire_date')
        service_type = request.data.get('service_type', 'publication_fee')

        if not card_number or not expire_date:
            return Response({'error': 'Card number and expire date are required'}, status=400)

        service = ClickPaymentService.get_service_for_service_type(service_type)
        result = service.request_card_token(
            service_id=service.service_id,
            card_number=card_number,
            expire_date=expire_date
        )

        return Response(result)
    except Exception as e:
        logger.error(f"Error requesting card token: {str(e)}")
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_card_token_view(request):
    """Verify card token with SMS code"""
    try:
        card_token = request.data.get('card_token')
        sms_code = request.data.get('sms_code')
        service_type = request.data.get('service_type', 'publication_fee')

        if not card_token or not sms_code:
            return Response({'error': 'Card token and SMS code are required'}, status=400)

        service = ClickPaymentService.get_service_for_service_type(service_type)
        result = service.verify_card_token(
            service_id=service.service_id,
            card_token=card_token,
            sms_code=sms_code
        )

        return Response(result)
    except Exception as e:
        logger.error(f"Error verifying card token: {str(e)}")
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_with_card_token_view(request):
    """Pay with verified card token"""
    try:
        card_token = request.data.get('card_token')
        amount = request.data.get('amount')
        transaction_id = request.data.get('transaction_id')
        service_type = request.data.get('service_type', 'publication_fee')

        if not card_token or not amount or not transaction_id:
            return Response({'error': 'Card token, amount and transaction_id are required'}, status=400)

        # Get or create transaction
        try:
            transaction = Transaction.objects.get(id=transaction_id, user=request.user)
        except Transaction.DoesNotExist:
            return Response({'error': 'Transaction not found'}, status=404)

        service = ClickPaymentService.get_service_for_service_type(service_type)
        result = service.pay_with_card_token(
            service_id=service.service_id,
            card_token=card_token,
            amount=float(amount),
            merchant_trans_id=str(transaction.id)
        )

        # Update transaction status based on result
        if result.get('error') == 0:
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save()

        return Response(result)
    except Exception as e:
        logger.error(f"Error paying with card token: {str(e)}")
        return Response({'error': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class ClickPaymentView(View):
    """Handle Click payment system callbacks"""

    def post(self, request):
        """Handle Click payment callbacks"""
        try:
            # Get JSON data from request
            data = json.loads(request.body)
            logger.info(f"Click payment callback received: {data}")

            # Get service_id from callback data to use correct service settings
            service_id = data.get('service_id')
            click_service = ClickPaymentService(service_id=service_id)

            # Handle the complete callback using the service
            result = click_service.handle_complete(data)

            logger.info(f"Click payment callback processed: {result}")

            return JsonResponse(result)

        except Exception as e:
            logger.error(f"Error processing Click payment callback: {str(e)}")
            return JsonResponse({
                'error': -1,
                'error_note': str(e)
            }, status=400)