from django.test import TestCase

from core.models import Role

from core.test_helpers import create_test_interactive_user
from policyholder.models import PolicyHolderUser
from policyholder.tests import create_test_policy_holder
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.services import validate_acquire_unassigned_voucher


class ValidateAcquireUnassignedTestCase(TestCase):
    user = None
    insuree = None
    policyholder = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(ValidateAcquireUnassignedTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.policyholder = create_test_policy_holder()

        policyholderuser = PolicyHolderUser(user=cls.user, policy_holder=cls.policyholder)
        policyholderuser.save(username=cls.user.username)

    def test_validate_success(self):
        payload = (
            self.user,
            self.policyholder.code,
            1
        )

        res = validate_acquire_unassigned_voucher(*payload)
        self.assertTrue(res['success'])
        self.assertEquals(res['data']['count'], 1)

    def test_validate_count_too_low(self):
        payload = (
            self.user,
            self.policyholder.code,
            0
        )

        res = validate_acquire_unassigned_voucher(*payload)
        self.assertFalse(res['success'])

    def test_validate_count_too_high(self):
        payload = (
            self.user,
            self.policyholder.code,
            WorkerVoucherConfig.max_generic_vouchers + 1
        )

        res = validate_acquire_unassigned_voucher(*payload)
        self.assertFalse(res['success'])

    def test_validate_ph_not_exists(self):
        payload = (
            self.user,
            "non existent ph code",
            1
        )

        res = validate_acquire_unassigned_voucher(*payload)
        self.assertFalse(res['success'])
