import base64
import csv
import logging
import re
from io import StringIO
from django.http import StreamingHttpResponse
from django.conf import settings
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Lead
from .serializers import LeadSerializer
from .services import DeliverabilityPolicyChecker, EmailVerifier, LeadGenerator
from .tasks import generate_leads_task

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def hello_world(request):
    """Simple hello world endpoint"""
    return Response({"message": "Welcome to Lead Generator API"})

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """API health check endpoint"""
    return Response({
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
    })

@api_view(['GET'])
def export_leads(request):
    """Export all leads as CSV"""
    class Echo:
        def write(self, value):
            return value

    leads = Lead.objects.filter(
        owner=request.user,
        is_verified=True,
    ).order_by('-created_at').iterator(chunk_size=500)

    writer = csv.writer(Echo())

    def rows():
        yield writer.writerow([
            'ID', 'Email', 'Phone', 'Source', 'Category', 'Location',
            'Created At', 'Link', 'Problem Statement',
        ])
        for lead in leads:
            yield writer.writerow([
                lead.id, lead.email, lead.phone, lead.source, lead.category,
                lead.location, lead.created_at.isoformat(), lead.link,
                lead.problem_statement,
            ])

    response = StreamingHttpResponse(rows(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="verified_leads.csv"'
    return response

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class LeadListView(ListAPIView):
    serializer_class = LeadSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Lead.objects.filter(owner=self.request.user).order_by('-created_at')

class DeleteLeadView(APIView):
    def delete(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk, owner=request.user)
            lead.delete()
            return Response({"message": f"Lead {pk} deleted successfully"}, status=status.HTTP_200_OK)
        except Lead.DoesNotExist:
            return Response({"error": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)

class GenerateLeadsView(APIView):
    # Rate limit is recorded but not auto-blocked, so staff/admin ("premium")
    # accounts can bypass it. The premium flag is the authenticated user's
    # is_staff bit — set securely via `manage.py createsuperuser`, never in code.
    @method_decorator(ratelimit(key='ip', rate='5/5m', block=False))
    def post(self, request):
        if getattr(request, 'limited', False) and not request.user.is_staff:
            return Response(
                {"error": "Rate limit exceeded. Try again shortly, or use an admin (premium) account."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        category = request.data.get('category')
        if not category:
            return Response({"error": "category is required"}, status=status.HTTP_400_BAD_REQUEST)

        platforms = request.data.get('platforms', ['x', 'reddit'])
        niche = request.data.get('niche')
        target_location = request.data.get('target_location')
        is_professional = request.data.get('is_professional', False)
        sender_email = request.data.get('sender_email') or settings.DEFAULT_FROM_EMAIL

        # Validate inputs
        if not platforms:
            return Response({"error": "At least one platform must be selected"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Lead generation request: category={category}, platforms={platforms}, location={target_location}, is_professional={is_professional}")

        try:
            if settings.LEADGEN_SYNC_REQUESTS:
                generator = LeadGenerator()
                leads = generator.generate_leads(
                    category,
                    platforms,
                    niche,
                    target_location,
                    is_professional,
                    owner=request.user,
                )
            else:
                async_result = generate_leads_task.delay(
                    request.user.id,
                    category,
                    platforms,
                    niche,
                    target_location,
                    is_professional,
                )
                return Response({
                    "message": "Lead generation queued",
                    "task_id": async_result.id,
                    "timestamp": timezone.now().isoformat(),
                }, status=status.HTTP_202_ACCEPTED)
            
            logger.info(f"Generated {len(leads)} leads for category={category}")

            # Return CSV for download
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Email", "Phone", "Source", "Category", "Location", "Problem Statement", "Link"])

            for lead in leads:
                writer.writerow([
                    lead['email'], lead.get('phone', ''), lead['source'], category,
                    lead['location'], lead['problem_statement'], lead['link']
                ])

            base64_csv = base64.b64encode(output.getvalue().encode('utf-8')).decode('utf-8')

            return Response({
                "message": f"Generated {len(leads)} leads",
                "csv_base64": base64_csv,
                "leads": leads,
                "timestamp": timezone.now().isoformat(),
                "search_criteria": {
                    "category": category,
                    "niche": niche,
                    "location": target_location,
                    "platforms": platforms,
                    "professional_mode": is_professional,
                    "sender_email": sender_email,
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Lead generation error: {str(e)}", exc_info=True)
            return Response({
                "error": f"Failed to generate leads: {str(e)}",
                "details": "Check your API keys and try with different search parameters"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyLeadView(APIView):
    def post(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk, owner=request.user)
            lead.is_verified = EmailVerifier.is_valid_email(lead.email)
            lead.save()
            return Response({
                "id": lead.id,
                "email": lead.email,
                "is_verified": lead.is_verified
            })
        except Lead.DoesNotExist:
            return Response({"error": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)

class BulkVerifyLeadsView(APIView):
    def post(self, request):
        unverified = Lead.objects.filter(owner=request.user, is_verified=False)
        total = unverified.count()
        batch = unverified[:50]  # Process in batches
        verified_count = 0

        for lead in batch:
            if EmailVerifier.is_valid_email(lead.email):
                lead.is_verified = True
                lead.save()
                verified_count += 1

        return Response({
            "processed": batch.count(),
            "verified": verified_count,
            "remaining": total - batch.count()
        })

class VerifySingleEmailView(APIView):
    @method_decorator(ratelimit(key='user_or_ip', rate='30/5m', block=True))
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "email is required"}, status=status.HTTP_400_BAD_REQUEST)

        is_valid = EmailVerifier.is_valid_email(email)
        return Response({
            "email": email,
            "is_verified": is_valid,
            "message": "Valid email" if is_valid else "Invalid or unreachable email"
        })

class MultiVerifyView(APIView):
    @method_decorator(ratelimit(key='user_or_ip', rate='10/5m', block=True))
    def post(self, request):
        emails = request.data.get('emails', [])
        if not emails:
            return Response({"error": "emails list is required"}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for email in emails[:100]:  # Limit batch size
            is_valid = EmailVerifier.is_valid_email(email)
            results.append({
                "email": email,
                "is_verified": is_valid,
                "message": "Valid" if is_valid else "Invalid"
            })

        return Response({"results": results})

class FileUploadVerifyView(APIView):
    @method_decorator(ratelimit(key='user_or_ip', rate='5/5m', block=True))
    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "File is required"}, status=status.HTTP_400_BAD_REQUEST)
        if file_obj.size > settings.MAX_VERIFY_UPLOAD_BYTES:
            return Response({
                "error": f"File exceeds {settings.MAX_VERIFY_UPLOAD_BYTES} bytes"
            }, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        content = file_obj.read().decode('utf-8', errors='ignore')
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)))

        results = []
        for email in emails[:100]:  # Limit processing
            is_valid = EmailVerifier.is_valid_email(email)
            results.append({
                "email": email,
                "is_verified": is_valid,
                "message": "Valid" if is_valid else "Invalid"
            })

        return Response({
            "filename": file_obj.name,
            "found_emails": len(emails),
            "processed": len(results),
            "results": results
        })

class DeliverabilityPolicyCheckView(APIView):
    @method_decorator(ratelimit(key='user_or_ip', rate='20/hour', block=True))
    def post(self, request):
        sender_email = request.data.get('sender_email') or settings.DEFAULT_FROM_EMAIL
        subject = request.data.get('subject', '')
        body = request.data.get('body', '')
        daily_volume = request.data.get('daily_volume')
        include_unsubscribe = request.data.get('include_unsubscribe')
        dkim_selectors = request.data.get('dkim_selectors') or []

        if isinstance(dkim_selectors, str):
            dkim_selectors = [
                selector.strip()
                for selector in dkim_selectors.split(',')
                if selector.strip()
            ]

        try:
            result = DeliverabilityPolicyChecker.check(
                sender_email=sender_email,
                subject=subject,
                body=body,
                daily_volume=daily_volume,
                include_unsubscribe=include_unsubscribe,
                dkim_selectors=dkim_selectors,
                smtp_host=settings.EMAIL_HOST,
                smtp_tls=settings.EMAIL_USE_TLS,
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Deliverability policy check failed: {e}", exc_info=True)
            return Response({
                "error": "Failed to run deliverability policy check",
                "details": str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FirebaseTokenExchangeView(APIView):
    """Exchange a verified Firebase ID token for a Django SimpleJWT pair.

    The Firebase ID token is validated by the default authentication chain
    (``FirebaseAuthentication``). On success we mint a Django access/refresh
    pair for the mapped user so the client can use Django-issued JWTs for all
    subsequent API calls.
    """

    def post(self, request):
        refresh = RefreshToken.for_user(request.user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
            },
        }, status=status.HTTP_200_OK)
