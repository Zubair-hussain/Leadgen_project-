import base64
import csv
import logging
import os
from io import StringIO
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
from .models import Lead
from .serializers import LeadSerializer
from .services import DeliverabilityPolicyChecker, EmailVerifier, LeadGenerator

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
        "db_connected": Lead.objects.exists(),
        "serpapi_ready": bool(os.getenv('SERPAPI_KEY')),
        "google_cse_ready": bool(os.getenv('GOOGLE_API_KEY') and os.getenv('GOOGLE_CX')),
        "apify_ready": bool(os.getenv('APIFY_API_KEY') and os.getenv('APIFY_API_KEY') != "your_apify_api_key_here"),
        "gemini_ready": bool(os.getenv('GEMINI_API_KEY')),
        "sender": {
            "provider": "Gmail",
            "email": settings.DEFAULT_FROM_EMAIL,
            "host": settings.EMAIL_HOST,
            "configured": bool(settings.EMAIL_HOST_USER),
        },
        "timestamp": timezone.now().isoformat(),
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def export_leads(request):
    """Export all leads as CSV"""
    leads = Lead.objects.filter(is_verified=True).order_by('-created_at')
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Email', 'Phone', 'Source', 'Category', 'Location', 'Created At', 'Link', 'Problem Statement'])

    for lead in leads:
        writer.writerow([
            lead.id, lead.email, lead.phone, lead.source, lead.category,
            lead.location, lead.created_at.isoformat(), lead.link, lead.problem_statement
        ])

    return Response({
        "csv_base64": base64.b64encode(output.getvalue().encode('utf-8')).decode('utf-8'),
        "filename": "verified_leads.csv",
        "count": leads.count()
    })

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class LeadListView(ListAPIView):
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [AllowAny]

class DeleteLeadView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk)
            lead.delete()
            return Response({"message": f"Lead {pk} deleted successfully"}, status=status.HTTP_200_OK)
        except Lead.DoesNotExist:
            return Response({"error": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)

class GenerateLeadsView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='5/5m', block=True))
    def post(self, request):
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
            generator = LeadGenerator()
            leads = generator.generate_leads(category, platforms, niche, target_location, is_professional)
            
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
    permission_classes = [AllowAny]

    def post(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk)
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
    permission_classes = [AllowAny]

    def post(self, request):
        unverified = Lead.objects.filter(is_verified=False)
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
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "File is required"}, status=status.HTTP_400_BAD_REQUEST)

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
    permission_classes = [AllowAny]

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
