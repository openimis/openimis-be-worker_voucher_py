from django.test import TestCase

from core import datetime

from core.test_helpers import create_test_interactive_user
from insuree.test_helpers import create_test_insuree
from policyholder.tests import create_test_policy_holder
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import get_voucher_worker_enquire_filters


class WorkerEnquireTestCase(TestCase):
    user = None
    insuree = None
    policyholder = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(WorkerEnquireTestCase, cls).setUpClass()

        cls.user = create_test_interactive_user()
        cls.insuree = create_test_insuree(with_family=False, )
        cls.policyholder = create_test_policy_holder()

        cls.today = datetime.datetime.now()
        cls.tomorrow = datetime.datetime.now() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.datetime.now() - datetime.datetimedelta(days=1)

    def test_valid_voucher(self):
        voucher = self._create_test_voucher()
        query = WorkerVoucher.objects.filter(*get_voucher_worker_enquire_filters(self.insuree.chf_id), id=voucher.id)
        self.assertTrue(query.exists())

    def test_no_national_id(self):
        query = WorkerVoucher.objects.filter(*get_voucher_worker_enquire_filters(""))
        self.assertFalse(query.exists())

    def test_invalid_national_id(self):
        query = WorkerVoucher.objects.filter(*get_voucher_worker_enquire_filters("1231231231231"))
        self.assertFalse(query.exists())

    def test_expired_voucher(self):
        voucher = self._create_test_voucher(assigned_date=self.yesterday, expiry_date=self.today)
        query = WorkerVoucher.objects.filter(id=voucher.id)
        self.assertTrue(query.exists())
        query = WorkerVoucher.objects.filter(*get_voucher_worker_enquire_filters(self.insuree.chf_id), id=voucher.id)
        self.assertFalse(query.exists())

    def _create_test_voucher(self, code="001", status=WorkerVoucher.Status.ASSIGNED, assigned_date=None,
                             expiry_date=None):
        voucher = WorkerVoucher(
            insuree=self.insuree,
            policyholder=self.policyholder,
            code=code,
            status=status,
            assigned_date=self.today if not assigned_date else assigned_date,
            expiry_date=self.tomorrow if not expiry_date else expiry_date,
        )
        voucher.save(username=self.user.username)
        return voucher
