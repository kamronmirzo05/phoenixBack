"""
Click Payment Integration Service
"""
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import hashlib
import time
import requests
import json
import logging
import os
from .models import Transaction

# Set up logging
logger = logging.getLogger(__name__)

class ClickPaymentService:
    """Service for Click payment integration"""
    
    def __init__(self, service_id=None):
        # Load settings based on service_id or use default
        if service_id and service_id in getattr(settings, 'CLICK_SETTINGS', {}):
            click_config = settings.CLICK_SETTINGS[service_id]
            self.merchant_id = click_config['MERCHANT_ID']
            self.service_id = click_config['SERVICE_ID']
            self.secret_key = click_config['SECRET_KEY']
            self.merchant_user_id = click_config['MERCHANT_USER_ID']
        else:
            # Use default settings
            self.merchant_id = os.getenv('CLICK_MERCHANT_ID', '45730')
            self.service_id = os.getenv('CLICK_SERVICE_ID', '82154')
            self.secret_key = os.getenv('CLICK_SECRET_KEY', 'XZC6u3JBBh')
            self.merchant_user_id = os.getenv('CLICK_MERCHANT_USER_ID', '63536')
        
        self.api_url = "https://api.click.uz/v2/merchant"
        
        logger.info(f"ClickPaymentService initialized with: merchant_id={self.merchant_id}, service_id={self.service_id}, merchant_user_id={self.merchant_user_id}")
    
    @classmethod
    def get_service_for_service_type(cls, service_type):
        """Get appropriate Click service based on service type"""
        service_mapping = {
            'publication_fee': '82154',  # Ilmiyfaoliyat.uz
            'translation_fee': '82155',  # Phoenix publication
            'review_fee': '89248',       # Phoenix
        }
        service_id = service_mapping.get(service_type, '82154')
        return cls(service_id=service_id)
    
    def generate_auth_header(self):
        """Generate Auth header for Click API requests"""
        timestamp = str(int(time.time()))
        digest_string = timestamp + self.secret_key
        digest = hashlib.sha1(digest_string.encode('utf-8')).hexdigest()
        auth_header = f"{self.merchant_user_id}:{digest}:{timestamp}"
        logger.info(f"Generated auth header: {auth_header}")
        return auth_header
    
    def create_invoice(self, service_id, amount, phone_number, merchant_trans_id):
        """Create invoice for payment"""
        url = f"{self.api_url}/invoice/create"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        payload = {
            "service_id": service_id,
            "amount": float(amount),
            "phone_number": phone_number,
            "merchant_trans_id": merchant_trans_id
        }
        
        logger.info(f"Sending request to {url} with payload: {payload}")
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            logger.info(f"Response status: {response.status_code}, content: {response.text}")
            return response.json()
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return {"error_code": -1, "error_note": str(e)}
    
    def generate_signature(self, *args):
        """Generate signature for Click request"""
        # Click uses MD5 hash for signature generation
        # According to documentation: sign_string = args + secret_key
        sign_string = ''.join(str(arg) for arg in args) + self.secret_key
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    def prepare_payment(self, transaction):
        """Prepare payment data for Click"""
        # Bu metod endi create_invoice metodidan foydalanadi
        return self.create_invoice(
            service_id=self.service_id,
            amount=float(transaction.amount),
            phone_number=getattr(transaction.user, 'phone', ''),
            merchant_trans_id=str(transaction.id)
        )
    
    def get_payment_url(self, transaction, return_url=None):
        """Generate Click payment URL"""
        base_url = "https://my.click.uz/services/pay"
        
        params = {
            'service_id': self.service_id,
            'merchant_id': self.merchant_id,
            'amount': float(transaction.amount),
            'transaction_param': str(transaction.id),
        }
        
        if return_url:
            params['return_url'] = return_url
        
        # Generate URL with parameters
        url_params = '&'.join([f"{key}={value}" for key, value in params.items()])
        payment_url = f"{base_url}?{url_params}"
        
        logger.info(f"Generated payment URL: {payment_url}")
        return payment_url
    
    def handle_prepare(self, data):
        """Handle Click prepare request"""
        try:
            click_trans_id = data.get('click_trans_id')
            service_id = data.get('service_id')
            merchant_trans_id = data.get('merchant_trans_id')
            amount = data.get('amount')
            action = data.get('action')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            logger.info(f"Handling prepare request with data: click_trans_id={click_trans_id}, service_id={service_id}, merchant_trans_id={merchant_trans_id}, amount={amount}, action={action}, sign_time={sign_time}")
            
            # Validate required fields
            if not all([click_trans_id, service_id, merchant_trans_id, amount, action, sign_time]):
                logger.error("Missing required fields")
                return {'error': -8, 'error_note': 'Missing required fields'}
            
            # Verify signature according to Click documentation
            expected_sign = self.generate_signature(
                click_trans_id, service_id, merchant_trans_id, amount, action, sign_time
            )
            
            logger.info(f"Expected signature: {expected_sign}, received signature: {sign_string}")
            
            if sign_string != expected_sign:
                logger.error("Invalid signature")
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            # Find transaction
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
                logger.info(f"Found transaction: {transaction.id}, amount: {transaction.amount}")
            except (ObjectDoesNotExist, ValueError):
                logger.error(f"Transaction not found: {merchant_trans_id}")
                return {'error': -5, 'error_note': 'User not found'}
            
            # Check amount (convert to float for comparison)
            try:
                request_amount = float(amount)
                transaction_amount = float(transaction.amount)
                if abs(request_amount - transaction_amount) > 0.01:  # Allow small floating point differences
                    logger.error(f"Amount mismatch: request={request_amount}, transaction={transaction_amount}")
                    return {'error': -2, 'error_note': 'Invalid amount'}
            except (ValueError, TypeError):
                logger.error(f"Invalid amount format: {amount}")
                return {'error': -2, 'error_note': 'Invalid amount'}
            
            # Check if transaction is already processed
            if transaction.status == 'completed':
                logger.warning(f"Transaction {merchant_trans_id} already completed")
                return {
                    'click_trans_id': click_trans_id,
                    'merchant_trans_id': merchant_trans_id,
                    'merchant_prepare_id': transaction.id,
                    'error': 0,
                    'error_note': 'Success'
                }
            
            # Update transaction
            transaction.click_trans_id = click_trans_id
            transaction.status = 'pending'
            transaction.save()
            
            return {
                'click_trans_id': int(click_trans_id),
                'merchant_trans_id': merchant_trans_id,
                'merchant_prepare_id': int(transaction.id),
                'error': 0,
                'error_note': 'Success'
            }
            
        except Exception as e:
            logger.error(f"Error in handle_prepare: {str(e)}")
            return {'error': -9, 'error_note': 'System error'}
    
    def handle_complete(self, data):
        """Handle Click complete request"""
        try:
            click_trans_id = data.get('click_trans_id')
            merchant_trans_id = data.get('merchant_trans_id')
            merchant_prepare_id = data.get('merchant_prepare_id')
            error = data.get('error')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            logger.info(f"Handling complete request with data: click_trans_id={click_trans_id}, merchant_trans_id={merchant_trans_id}, merchant_prepare_id={merchant_prepare_id}, error={error}, sign_time={sign_time}")
            
            # Validate required fields
            if not all([click_trans_id, merchant_trans_id, sign_time]):
                logger.error("Missing required fields in complete request")
                return {'error': -8, 'error_note': 'Missing required fields'}
            
            # Verify signature for complete request
            expected_sign = self.generate_signature(
                click_trans_id, merchant_trans_id, merchant_prepare_id or '', error or 0, sign_time
            )
            
            logger.info(f"Expected signature: {expected_sign}, received signature: {sign_string}")
            
            if sign_string != expected_sign:
                logger.error("Invalid signature in complete request")
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            # Find transaction
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
                logger.info(f"Found transaction for complete: {transaction.id}, status: {transaction.status}")
            except (ObjectDoesNotExist, ValueError):
                logger.error(f"Transaction not found in complete: {merchant_trans_id}")
                return {'error': -5, 'error_note': 'User not found'}
            
            # Update transaction based on Click's error code
            if error == 0 or error == '0':
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
                transaction.click_paydoc_id = data.get('click_paydoc_id', '')
                logger.info(f"Transaction {merchant_trans_id} completed successfully")
            else:
                transaction.status = 'failed'
                transaction.error_code = str(error)
                transaction.error_note = data.get('error_note', 'Payment failed')
                logger.warning(f"Transaction {merchant_trans_id} failed with error: {error}")
            
            transaction.save()
            
            return {
                'click_trans_id': int(click_trans_id),
                'merchant_trans_id': merchant_trans_id,
                'merchant_confirm_id': int(transaction.id),
                'error': 0,
                'error_note': 'Success'
            }
            
        except Exception as e:
            logger.error(f"Error in handle_complete: {str(e)}")
            return {'error': -9, 'error_note': 'System error'}