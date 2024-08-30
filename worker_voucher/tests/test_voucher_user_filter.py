from django.test import TestCase

from core import datetime
from core.models import Role

from core.test_helpers import create_test_interactive_user
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import get_voucher_user_filters
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker_for_eu


class VoucherUserTestCase(TestCase):
    user = None
    user2 = None
    user_admin = None
    worker = None
    eu = None
    eu2 = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(VoucherUserTestCase, cls).setUpClass()

        role_admin, role_employer = [
            Role.objects.get(name='IMIS Administrator', validity_to__isnull=True),
            Role.objects.get(name='Employer', validity_to__isnull=True),
        ]

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.user2 = create_test_interactive_user(username='VoucherTestUser2', roles=[role_employer.id])
        cls.user_admin = create_test_interactive_user(username='VoucherTestUserAdmin', roles=[role_admin.id])

        cls.eu = create_test_eu_for_user(cls.user)
        cls.eu2 = create_test_eu_for_user(cls.user2)

        cls.worker = create_test_worker_for_eu(cls.user, cls.eu)

        cls.today = datetime.datetime.now()
        cls.tomorrow = datetime.datetime.now() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.datetime.now() - datetime.datetimedelta(days=1)

    def test_correct_user(self):
        self._create_test_voucher()
        query = WorkerVoucher.objects.filter(*get_voucher_user_filters(self.user.i_user))
        self.assertTrue(query.exists())

    def test_wrong_user(self):
        self._create_test_voucher()
        query = WorkerVoucher.objects.filter(*get_voucher_user_filters(self.user2.i_user))
        self.assertFalse(query.exists())

    def test_all_voucher_right_user(self):
        self._create_test_voucher()
        query = WorkerVoucher.objects.filter(*get_voucher_user_filters(self.user_admin.i_user))
        self.assertTrue(query.exists())

    def _create_test_voucher(self, code="001", policyholder=None, status=WorkerVoucher.Status.ASSIGNED,
                             assigned_date=None, expiry_date=None):
        voucher = WorkerVoucher(
            insuree=self.worker,
            policyholder=self.eu if not policyholder else policyholder,
            code=code,
            status=status,
            assigned_date=self.today if not assigned_date else assigned_date,
            expiry_date=self.tomorrow if not expiry_date else expiry_date,
        )
        voucher.save(username=self.user.username)
