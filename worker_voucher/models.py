from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import HistoryModel
from core import fields
from insuree.models import Insuree
from policyholder.models import PolicyHolder
from graphql import ResolveInfo


class WorkerVoucher(HistoryModel):
    class Status(models.TextChoices):
        AWAITING_PAYMENT = 'AWAITING_PAYMENT', _('Awaiting Payment')
        UNASSIGNED = 'UNASSIGNED', _('Unassigned')
        ASSIGNED = 'ASSIGNED', _('Assigned')
        EXPIRED = 'EXPIRED', _('Expired')
        CANCELED = 'CANCELED', _('Canceled')
        CLOSED = 'CLOSED', _('Closed')

    insuree = models.ForeignKey(Insuree, null=True, blank=True, on_delete=models.DO_NOTHING)
    policyholder = models.ForeignKey(PolicyHolder, null=True, blank=True, on_delete=models.DO_NOTHING)
    code = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True, choices=Status.choices,
                              default=Status.AWAITING_PAYMENT)
    assigned_date = fields.DateTimeField(blank=True, null=True)
    expiry_date = fields.DateTimeField(blank=True, null=True)

    @classmethod
    def get_queryset(cls, queryset, user):
        from worker_voucher.services import get_voucher_user_filters

        queryset = cls.filter_queryset(queryset)
        if isinstance(user, ResolveInfo):
            user = user.context.user
        if settings.ROW_SECURITY:
            if user.is_anonymous:
                queryset = queryset.filter(id=None)
            queryset = queryset.filter(*get_voucher_user_filters(user))
        return queryset
