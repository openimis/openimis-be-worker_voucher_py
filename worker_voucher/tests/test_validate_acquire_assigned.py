from django.test import TestCase

from core import datetime
from core.models import Role

from core.test_helpers import create_test_interactive_user
from worker_voucher.services import validate_acquire_assigned_vouchers
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker_for_eu


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
