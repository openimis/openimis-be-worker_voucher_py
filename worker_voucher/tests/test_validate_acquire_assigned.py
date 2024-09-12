from dateutils import years
from django.test import TestCase

from core import datetime
from core.models import Role
from core.test_helpers import create_test_interactive_user
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.services import validate_acquire_assigned_vouchers, create_assigned_voucher
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker_for_eu, \
    OverrideAppConfig as override_config


class ValidateAcquireAssignedTestCase(TestCase):
    user = None
    eu = None
    worker = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(ValidateAcquireAssignedTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu)

        cls.today = datetime.date.today()
        cls.tomorrow = datetime.date.today() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.date.today() - datetime.datetimedelta(days=1)

    def test_validate_success(self):
        payload = (
            self.user,
            self.eu.code,
            (self.worker.chf_id,),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertTrue(res['success'])
        self.assertEquals(res['data']['count'], 1)

    def test_validate_ins_not_exists(self):
        payload = (
            self.user,
            self.eu.code,
            ("non existent chfid",),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertFalse(res['success'])

    def test_validate_ph_not_exists(self):
        payload = (
            self.user,
            "non existent ph code",
            (self.worker.chf_id,),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertFalse(res['success'])

    def test_validate_dates_overlap(self):
        payload = (
            self.user,
            self.eu.code,
            (self.worker.chf_id,),
            ({'start_date': self.yesterday, 'end_date': self.today},
             {'start_date': self.today, 'end_date': self.tomorrow},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertFalse(res['success'])

    @override_config(WorkerVoucherConfig, {"voucher_expiry_type": "end_of_year"})
    def test_validate_end_of_year(self):
        end_of_year = datetime.date(datetime.date.today().year, 12, 31)

        payload = (
            self.user,
            self.eu.code,
            (self.worker.chf_id,),
            ([{'start_date': end_of_year, 'end_date': end_of_year}])
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertTrue(res['success'])

    @override_config(WorkerVoucherConfig, {"yearly_worker_voucher_limit": 3,
                                           "voucher_expiry_type": "fixed_period",
                                           "voucher_expiry_period": {"years": 2}})
    def test_validate_worker_voucher_limit_reached(self):
        voucher_limit = WorkerVoucherConfig.yearly_worker_voucher_limit
        date_start = datetime.date(datetime.date.today().year + 1, 1, 1)
        self._acquire_vouchers(date_start, voucher_limit)

        date_test = date_start + datetime.datetimedelta(days=voucher_limit)

        payload = (
            self.user,
            self.eu.code,
            (self.worker.chf_id,),
            ([{'start_date': date_test, 'end_date': date_test}])
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertFalse(res['success'])

    @override_config(WorkerVoucherConfig, {"yearly_worker_voucher_limit": 3,
                                           "voucher_expiry_type": "fixed_period",
                                           "voucher_expiry_period": {"years": 2}})
    def test_validate_worker_voucher_limit_next_year(self):
        voucher_limit = WorkerVoucherConfig.yearly_worker_voucher_limit
        date_start = datetime.date(datetime.date.today().year + 1, 1, 1)
        self._acquire_vouchers(date_start, voucher_limit)

        date_test = date_start + datetime.datetimedelta(years=1)

        payload = (
            self.user,
            self.eu.code,
            (self.worker.chf_id,),
            ([{'start_date': date_test, 'end_date': date_test}])
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertTrue(res['success'])

    def _acquire_vouchers(self, date_start, amount):
        dates = [date_start + datetime.datetimedelta(days=i) for i in range(amount)]

        for date in dates:
            create_assigned_voucher(self.user, date, self.worker.id, self.eu.id)
