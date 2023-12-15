from django.test import TestCase

from core import datetime
from core.models import Role

from core.test_helpers import create_test_interactive_user
from insuree.test_helpers import create_test_insuree
from policyholder.models import PolicyHolderUser
from policyholder.tests import create_test_policy_holder
from worker_voucher.services import validate_acquire_assigned_vouchers


class ValidateAcquireAssignedTestCase(TestCase):
    user = None
    insuree = None
    policyholder = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(ValidateAcquireAssignedTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.insuree = create_test_insuree(with_family=False)
        cls.policyholder = create_test_policy_holder()

        policyholderuser = PolicyHolderUser(user=cls.user, policy_holder=cls.policyholder)
        policyholderuser.save(username=cls.user.username)

        cls.today = datetime.date.today()
        cls.tomorrow = datetime.date.today() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.date.today() - datetime.datetimedelta(days=1)

    def test_validate_success(self):
        payload = (
            self.user,
            self.policyholder.code,
            (self.insuree.chf_id,),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertTrue(res['success'])
        self.assertEquals(res['data']['count'], 1)

    def test_validate_ins_not_exists(self):
        payload = (
            self.user,
            self.policyholder.code,
            ("non existent chfid",),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertFalse(res['success'])

    def test_validate_ph_not_exists(self):
        payload = (
            self.user,
            "non existent ph code",
            (self.insuree.chf_id,),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertFalse(res['success'])

    def test_validate_dates_overlap(self):
        payload = (
            self.user,
            self.policyholder.code,
            (self.insuree.chf_id,),
            ({'start_date': self.yesterday, 'end_date': self.today},
             {'start_date': self.today, 'end_date': self.tomorrow},)
        )

        res = validate_acquire_assigned_vouchers(*payload)

        self.assertFalse(res['success'])
