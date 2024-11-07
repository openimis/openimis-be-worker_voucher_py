from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import HistoryModel, HistoryBusinessModel, User
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
        PRINTED = 'PRINTED', _('Printed')

    insuree = models.ForeignKey(Insuree, null=True, blank=True, on_delete=models.DO_NOTHING)
    policyholder = models.ForeignKey(PolicyHolder, null=True, blank=True, on_delete=models.DO_NOTHING)
    code = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True, choices=Status.choices,
                              default=Status.AWAITING_PAYMENT)
    assigned_date = fields.DateTimeField(blank=True, null=True)
    expiry_date = fields.DateTimeField(blank=True, null=True)
    date_of_assignment = fields.DateTimeField(blank=True, null=True)

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


class WorkerUpload(HistoryModel):
    class Status(models.TextChoices):
        TRIGGERED = 'TRIGGERED', _('Triggered')
        IN_PROGRESS = 'IN_PROGRESS', _('In progress')
        SUCCESS = 'SUCCESS', _('Success')
        PARTIAL_SUCCESS = 'PARTIAL_SUCCESS', _('Partial success')
        FAIL = 'FAIL', _('Fail')

    policyholder = models.ForeignKey(PolicyHolder, models.DO_NOTHING, null=True, blank=True)
    status = models.CharField(max_length=255, choices=Status.choices, default=Status.TRIGGERED)
    error = models.JSONField(blank=True, default=dict)
    file_name = models.CharField(max_length=255, null=True, blank=True)


class GroupOfWorker(HistoryModel):
    name = models.CharField(max_length=50)
    policyholder = models.ForeignKey(PolicyHolder, models.DO_NOTHING, null=True, blank=True)

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


class WorkerGroup(HistoryBusinessModel):
    group = models.ForeignKey(GroupOfWorker, related_name="group_workers", on_delete=models.DO_NOTHING)
    insuree = models.ForeignKey(Insuree, null=True, blank=True, on_delete=models.DO_NOTHING)


class VoucherFormDraft(HistoryBusinessModel):
    class Type(models.TextChoices):
        ACQUIREMENT = 'ACQUIREMENT', _('acquirement')
        ASSIGNMENT = 'ASSIGNMENT', _('assignment')
    policyholder = models.ForeignKey(PolicyHolder, models.DO_NOTHING, null=False)
    user = models.ForeignKey(User, on_delete=models.deletion.DO_NOTHING, null=False, related_name='%(class)s_user_voucher')
    type = models.CharField(max_length=255, blank=True, null=True, choices=Type.choices,
                              default=Type.ASSIGNMENT)


class VoucherFormDraftWorkersDetails(HistoryBusinessModel):
    voucher_form_draft = models.ForeignKey(VoucherFormDraft, models.DO_NOTHING, null=False)
    insuree = models.ForeignKey(Insuree, null=True, blank=True, on_delete=models.DO_NOTHING)


class VoucherFormDraftDateRangesDetails(HistoryBusinessModel):
    voucher_form_draft = models.ForeignKey(VoucherFormDraft, models.DO_NOTHING, null=False)
    start_date = fields.DateField(blank=True, null=True)
    end_date = fields.DateField(blank=True, null=True)
