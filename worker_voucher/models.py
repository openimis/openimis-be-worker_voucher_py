from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import HistoryModel
from core import fields
from insuree.models import Insuree
from policyholder.models import PolicyHolder


class WorkerVoucher(HistoryModel):
    class Status(models.TextChoices):
        PENDING = 'AWAITING_PAYMENT', _('Awaiting Payment')
        UNASSIGNED = 'UNASSIGNED', _('Unassigned')
        ASSIGNED = 'ASSIGNED', _('Assigned')
        EXPIRED = 'EXPIRED', _('Expired')
        CANCELED = 'CANCELED', _('Canceled')
        CLOSED = 'CLOSED', _('Closed')

    insuree = models.ForeignKey(Insuree, null=True, blank=True, on_delete=models.DO_NOTHING)
    policyholder = models.ForeignKey(PolicyHolder, null=True, blank=True, on_delete=models.DO_NOTHING)
    code = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True, choices=Status.choices, default=Status.PENDING)
    assigned_date = fields.DateField(blank=True, null=True)
    expiry_date = fields.DateField(blank=True, null=True)
