"""
Click Payment Integration Service
"""
from django.conf import settings
from django.utils import timezone
import hashlib
import time
import requests
from .models import Transaction


class ClickPaymentService:
    """Service for Click payment integration"""
    
    def __init__(self, service_id=None):
        # Agar service_id berilmasa, default sozlamalardan foydalanamiz
        if service_id and str(service_id) in settings.CLICK_SETTINGS:
            service_settings = settings.CLICK_SETTINGS[str(service_id)]
            self.merchant_id = service_settings['MERCHANT_ID']
            self.service_id = service_settings['SERVICE_ID']
            self.secret_key = service_settings['SECRET_KEY']
            self.merchant_user_id = service_settings['MERCHANT_USER_ID']
        else:
            # Default sozlamalar
            self.merchant_id = settings.CLICK_MERCHANT_ID
            self.service_id = settings.CLICK_SERVICE_ID
            self.secret_key = settings.CLICK_SECRET_KEY
            self.merchant_user_id = settings.CLICK_MERCHANT_USER_ID
        
        self.api_url = "https://api.click.uz/v2/merchant"
    
    @classmethod
    def get_service_for_service_type(cls, service_type):
        """Service typega qarab mos Click xizmatini qaytaradi"""
        service_mapping = {
            'publication_fee': '82154',  # Ilmiyfaoliyat.uz
            'fast-track': '82155',       # Phoenix publication
            'translation': '89248',      # Phoenix
            'book_publication': '89248', # Phoenix
            'language_editing': '89248', # Phoenix
            'top_up': '82154',           # Ilmiyfaoliyat.uz
        }
        
        service_id = service_mapping.get(service_type, '82154')
        return cls(service_id=service_id)
    
    def generate_auth_header(self):
        """Generate Auth header for Click API requests"""
        timestamp = str(int(time.time()))
        digest_string = timestamp + self.secret_key
        digest = hashlib.sha1(digest_string.encode('utf-8')).hexdigest()
        return f"{self.merchant_user_id}:{digest}:{timestamp}"
    
    def generate_signature(self, *args):
        """Generate signature for Click request"""
        # Click uses MD5 hash for signature generation
        # According to documentation: sign_string = args + secret_key
        sign_string = ''.join(str(arg) for arg in args) + self.secret_key
        return hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    
    def create_invoice(self, service_id, amount, phone_number, merchant_trans_id):
        """Create invoice (sчет-фактура)"""
        url = f"{self.api_url}/invoice/create"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        data = {
            'service_id': service_id,
            'amount': amount,
            'phone_number': phone_number,
            'merchant_trans_id': merchant_trans_id
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def check_invoice_status(self, service_id, invoice_id):
        """Check invoice status"""
        url = f"{self.api_url}/invoice/status/{service_id}/{invoice_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def check_payment_status(self, service_id, payment_id):
        """Check payment status"""
        url = f"{self.api_url}/payment/status/{service_id}/{payment_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def check_payment_status_by_mti(self, service_id, merchant_trans_id, date):
        """Check payment status by merchant_trans_id"""
        url = f"{self.api_url}/payment/status_by_mti/{service_id}/{merchant_trans_id}/{date}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.get(url, headers=headers)
        return response.json()
    
    def reverse_payment(self, service_id, payment_id):
        """Reverse (cancel) payment"""
        url = f"{self.api_url}/payment/reversal/{service_id}/{payment_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.delete(url, headers=headers)
        return response.json()
    
    def request_card_token(self, service_id, card_number, expire_date, temporary=1):
        """Request card token"""
        url = f"{self.api_url}/card_token/request"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        data = {
            'service_id': service_id,
            'card_number': card_number,
            'expire_date': expire_date,
            'temporary': temporary
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def verify_card_token(self, service_id, card_token, sms_code):
        """Verify card token"""
        url = f"{self.api_url}/card_token/verify"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        data = {
            'service_id': service_id,
            'card_token': card_token,
            'sms_code': sms_code
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def pay_with_card_token(self, service_id, card_token, amount, merchant_trans_id):
        """Pay with card token"""
        url = f"{self.api_url}/card_token/payment"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        data = {
            'service_id': service_id,
            'card_token': card_token,
            'amount': amount,
            'merchant_trans_id': merchant_trans_id
        }
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def delete_card_token(self, service_id, card_token):
        """Delete card token"""
        url = f"{self.api_url}/card_token/{service_id}/{card_token}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.delete(url, headers=headers)
        return response.json()
    
    def prepare_payment(self, transaction):
        """Prepare payment data for Click"""
        # Bu metod endi create_invoice metodidan foydalanadi
        return self.create_invoice(
            service_id=self.service_id,
            amount=float(transaction.amount),
            phone_number=getattr(transaction.user, 'phone', ''),
            merchant_trans_id=str(transaction.id)
        )
    
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
            
            # Verify signature according to Click documentation
            # sign_string = md5(click_trans_id + service_id + merchant_trans_id + amount + action + sign_time + secret_key)
            expected_sign = self.generate_signature(
                click_trans_id, service_id, merchant_trans_id, amount, action, sign_time
            )
            
            if sign_string != expected_sign:
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            # Find transaction
            try:
                transaction = Transaction.objects.get(id=merchant_trans_id)
            except Transaction.DoesNotExist:
                return {'error': -5, 'error_note': 'Transaction not found'}
            
            # Check amount
            if float(amount) != float(transaction.amount):
                return {'error': -2, 'error_note': 'Invalid amount'}
            
            # Save Click transaction ID
            transaction.click_trans_id = click_trans_id
            transaction.merchant_trans_id = merchant_trans_id
            transaction.save()
            
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'merchant_prepare_id': transaction.id,
                'error': 0,
                'error_note': 'Success'
            }
            
        except Exception as e:
            return {'error': -9, 'error_note': str(e)}
    
    def handle_complete(self, data):
        """Handle Click complete request"""
        try:
            click_trans_id = data.get('click_trans_id')
            merchant_trans_id = data.get('merchant_trans_id')
            merchant_prepare_id = data.get('merchant_prepare_id')
            error = data.get('error')
            sign_time = data.get('sign_time')
            sign_string = data.get('sign_string')
            
            # Verify signature for complete request according to Click documentation
            # sign_string = md5(click_trans_id + merchant_trans_id + merchant_prepare_id + error + sign_time + secret_key)
            expected_sign = self.generate_signature(
                click_trans_id, merchant_trans_id, merchant_prepare_id, error, sign_time
            )
            
            if sign_string != expected_sign:
                return {'error': -1, 'error_note': 'Invalid signature'}
            
            transaction = Transaction.objects.get(id=merchant_trans_id)
            
            # Only update status if payment is confirmed by Click system (error == 0)
            # This ensures that status is not set to 'completed' until real payment is confirmed
            if error == 0:
                # Verify that this is a real payment by checking additional data
                click_paydoc_id = data.get('click_paydoc_id', '')
                if click_paydoc_id:
                    transaction.status = 'completed'
                    transaction.completed_at = timezone.now()
                    transaction.click_paydoc_id = click_paydoc_id
                    transaction.click_trans_id = click_trans_id  # Store click transaction ID
                else:
                    # If no paydoc ID is provided, it's not a real payment yet
                    transaction.status = 'pending'
            else:
                # Payment failed according to Click system
                transaction.status = 'failed'
                transaction.error_code = error
                transaction.error_note = data.get('error_note', f'Payment failed with error code {error}')
            
            transaction.save()
            
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'merchant_confirm_id': transaction.id,
                'error': 0,
                'error_note': 'Success'
            }
            
        except Transaction.DoesNotExist:
            return {'error': -5, 'error_note': 'Transaction not found'}
        except Exception as e:
            return {'error': -9, 'error_note': str(e)}

    def send_receipt(self, transaction_id, amount, phone_number, email=None, items=None):
        """Fiscalization - send receipt to tax authority"""
        url = f"{self.api_url}/receipt/send"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        # Prepare receipt items
        if not items:
            items = [{
                'name': 'Publication Service',
                'count': 1,
                'price': amount,
                'total': amount,
                'payment_item_type': 1,  # Mehnat (Service)
                'tax_type': 1  # 0% NDS
            }]
        
        data = {
            'transaction_id': transaction_id,
            'service_id': self.service_id,
            'amount': amount,
            'phone_number': phone_number,
            'items': items
        }
        
        if email:
            data['email'] = email
        
        response = requests.post(url, json=data, headers=headers)
        return response.json()
    
    def check_receipt_status(self, receipt_id):
        """Check receipt status"""
        url = f"{self.api_url}/receipt/status/{receipt_id}"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Auth': self.generate_auth_header()
        }
        
        response = requests.get(url, headers=headers)
        return response.json()

    def get_payment_url(self, transaction, return_url=None, callback_url=None):
        """Generate payment URL for redirecting user to Click payment page"""
        # Agar return_url berilmagan bo'lsa, default URL o'rnatamiz
        if not return_url:
            # Frontend sahifangizga moslang
            return_url = 'http://localhost:5173/payment-success'
        
        # Agar callback_url berilmagan bo'lsa, default URL o'rnatamiz
        if not callback_url:
            callback_url = f'http://127.0.0.1:8000/api/click/callback/'  # Backend callback URL
        
        # Click to'lov sahifasiga o'tish uchun URL
        # Note: transaction_param should be merchant_trans_id for proper tracking
        payment_url = f"https://my.click.uz/services/pay?service_id={self.service_id}&" \
                    f"merchant_id={self.merchant_id}&" \
                    f"amount={transaction.amount}&" \
                    f"transaction_param={transaction.id}&" \
                    f"return_url={return_url}&" \
                    f"callback_url={callback_url}"
        
        return payment_url