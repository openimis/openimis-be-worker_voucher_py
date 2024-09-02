from uuid import uuid4

from django.test import TestCase
from core.models import Role
from core import datetime
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import validate_assign_vouchers
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker_for_eu


class ValidateAssignVouchersTestCase(TestCase):
    user = None
    eu = None
    worker = None
    unassigned_voucher = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(ValidateAssignVouchersTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu)

        cls.today = datetime.date.today()
        cls.tomorrow = datetime.date.today() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.date.today() - datetime.datetimedelta(days=1)

        cls.unassigned_voucher = WorkerVoucher(code=uuid4(), expiry_date=cls.tomorrow, policyholder=cls.eu,
                                               status=WorkerVoucher.Status.UNASSIGNED)
        cls.unassigned_voucher.save(username=cls.user.username)

    def test_validate_success(self):
        payload = (
            self.user,
            self.eu.code,
            (self.worker.chf_id,),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_assign_vouchers(*payload)
        self.assertTrue(res['success'], res.get('error'))
        self.assertEquals(res['data']['count'], 1)

    def test_validate_not_enough_vouchers(self):
        payload = (
            self.user,
            self.eu.code,
            (self.worker.chf_id,),
            ({'start_date': self.today, 'end_date': self.tomorrow},)
        )

        res = validate_assign_vouchers(*payload)
        self.assertFalse(res['success'])
