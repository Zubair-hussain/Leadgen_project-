from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from leads.models import Lead

from . import ai, batches
from .models import OutreachBatch, OutreachMessage, Suppression
from .serializers import OutreachMessageSerializer, SuppressionSerializer
from .services import mark_queued, preflight, queue_status


class OutreachMessageListView(generics.ListCreateAPIView):
    """GET drafts/sent history, POST a new draft (never sends directly)."""
    serializer_class = OutreachMessageSerializer

    def get_queryset(self):
        queryset = OutreachMessage.objects.filter(owner=self.request.user).select_related('lead')
        wanted = self.request.query_params.get('status')
        return queryset.filter(status=wanted) if wanted else queryset

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user, status=OutreachMessage.Status.DRAFT)


class OutreachMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OutreachMessageSerializer

    def get_queryset(self):
        return OutreachMessage.objects.filter(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        if self.get_object().status != OutreachMessage.Status.DRAFT:
            return Response({'error': 'Only drafts can be edited.'}, status=status.HTTP_409_CONFLICT)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if self.get_object().status in (OutreachMessage.Status.SENDING, OutreachMessage.Status.SENT):
            return Response({'error': 'Sent messages are kept as a record.'}, status=status.HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)


class ApproveMessageView(APIView):
    """Human approval: runs every safety check, then puts the draft in the send queue."""

    def post(self, request, pk):
        message = get_object_or_404(OutreachMessage, pk=pk, owner=request.user)
        if message.status != OutreachMessage.Status.DRAFT:
            return Response({'error': f'Message is {message.status}, not a draft.'}, status=status.HTTP_409_CONFLICT)
        problems = preflight(message)
        if problems:
            return Response({'error': 'Blocked by safety checks.', 'problems': problems},
                            status=status.HTTP_400_BAD_REQUEST)
        mark_queued(message)
        return Response(OutreachMessageSerializer(message, context={'request': request}).data)


class CancelMessageView(APIView):
    def post(self, request, pk):
        message = get_object_or_404(OutreachMessage, pk=pk, owner=request.user)
        if message.status not in (OutreachMessage.Status.DRAFT, OutreachMessage.Status.QUEUED):
            return Response({'error': f'Cannot cancel a {message.status} message.'}, status=status.HTTP_409_CONFLICT)
        message.status = OutreachMessage.Status.CANCELLED
        message.save(update_fields=['status', 'updated_at'])
        return Response(OutreachMessageSerializer(message, context={'request': request}).data)


class PreflightView(APIView):
    """Dry check a draft without approving it."""

    def get(self, request, pk):
        message = get_object_or_404(OutreachMessage, pk=pk, owner=request.user)
        problems = preflight(message)
        return Response({'ok': not problems, 'problems': problems})


class SuppressionListView(generics.ListCreateAPIView):
    serializer_class = SuppressionSerializer

    def get_queryset(self):
        return Suppression.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        suppression, created = Suppression.objects.get_or_create(
            owner=request.user, email=data['email'],
            defaults={'reason': data.get('reason', Suppression.Reason.MANUAL), 'note': data.get('note', '')},
        )
        # Anything still queued for this address must not go out.
        OutreachMessage.objects.filter(
            owner=request.user, to_email__iexact=suppression.email,
            status__in=[OutreachMessage.Status.DRAFT, OutreachMessage.Status.QUEUED],
        ).update(status=OutreachMessage.Status.CANCELLED, skip_reason='Recipient suppressed.')
        return Response(SuppressionSerializer(suppression).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class SuppressionDetailView(generics.DestroyAPIView):
    serializer_class = SuppressionSerializer

    def get_queryset(self):
        return Suppression.objects.filter(owner=self.request.user)


class OutreachStatusView(APIView):
    def get(self, request):
        return Response(queue_status())


class BatchListView(APIView):
    """GET recent batches. POST batches every current draft right now and emails you ONE review link."""

    def get(self, request):
        rows = OutreachBatch.objects.filter(owner=request.user)[:50]
        return Response([{
            'id': b.pk, 'status': b.status, 'created_at': b.created_at, 'auto_send_at': b.auto_send_at,
            'notified_at': b.notified_at, 'decided_at': b.decided_at, 'summary': b.summary,
            'messages': b.messages.count(),
        } for b in rows])

    def post(self, request):
        batch = batches.create_batch(request.user)
        if batch is None:
            return Response({'error': 'No drafts to review.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': batch.pk, 'status': batch.status, 'notified': batch.notified_at is not None,
                         'notify_error': batch.notify_error, 'messages': batch.messages.count()},
                        status=status.HTTP_201_CREATED)


class AiDraftsView(APIView):
    """Gemini writes drafts for verified leads. Drafts are never sent; they join the next review batch."""

    def post(self, request):
        leads = Lead.objects.filter(owner=request.user, is_verified=True).exclude(email__isnull=True).exclude(email='')
        ids = request.data.get('lead_ids')
        if ids:
            leads = leads.filter(pk__in=ids)
        leads = leads.exclude(
            outreach_messages__status__in=['draft', 'queued', 'sending', 'sent'],
        ).distinct()[:50]
        created, skipped = ai.write_drafts(request.user, list(leads))
        return Response({'created': [m.pk for m in created], 'skipped': skipped}, status=status.HTTP_201_CREATED)
