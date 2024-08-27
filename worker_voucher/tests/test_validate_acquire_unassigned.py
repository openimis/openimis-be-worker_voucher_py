from django.test import TestCase

from core.models import Role

from core.test_helpers import create_test_interactive_user
from worker_voucher.apps import WorkerVoucherConfig
from worker_voucher.services import validate_acquire_unassigned_vouchers
from worker_voucher.tests.util import create_test_eu_for_user


class ValidateAcquireUnassignedTestCase(TestCase):
    user = None
    eu = None

    @classmethod
    def setUpClass(cls):
        super(ValidateAcquireUnassignedTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)

    def test_validate_success(self):
        payload = (
            self.user,
            self.eu.code,
            1
        )

        res = validate_acquire_unassigned_vouchers(*payload)

        self.assertTrue(res['success'])
        self.assertEquals(res['data']['count'], 1)

    def test_validate_count_too_low(self):
        payload = (
            self.user,
            self.eu.code,
            0
        )

        res = validate_acquire_unassigned_vouchers(*payload)

        self.assertFalse(res['success'])

    def test_validate_count_too_high(self):
        payload = (
            self.user,
            self.eu.code,
            WorkerVoucherConfig.max_generic_vouchers + 1
        )

        res = validate_acquire_unassigned_vouchers(*payload)

        self.assertFalse(res['success'])

    def test_validate_ph_not_exists(self):
        payload = (
            self.user,
            "non existent ph code",
            1
        )

        res = validate_acquire_unassigned_vouchers(*payload)

        self.assertFalse(res['success'])
