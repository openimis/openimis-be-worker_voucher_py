from uuid import uuid4
from django.test import TestCase
from core.models import Role
from core import datetime
from core.test_helpers import create_test_interactive_user
from insuree.test_helpers import create_test_insuree
from policyholder.models import PolicyHolderUser
from policyholder.tests import create_test_policy_holder
from worker_voucher.models import WorkerVoucher
from worker_voucher.services import validate_assign_vouchers


class ValidateAssignVouchersTestCase(TestCase):
    user = None
    insuree = None
    policyholder = None
    unassigned_voucher = None

    today = None,
    yesterday = None,
    tomorrow = None

    @classmethod
    def setUpClass(cls):
        super(ValidateAssignVouchersTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.insuree = create_test_insuree(with_family=False)
        cls.policyholder = create_test_policy_holder()

        policyholderuser = PolicyHolderUser(user=cls.user, policy_holder=cls.policyholder)
        policyholderuser.save(username=cls.user.username)

        cls.today = datetime.date.today()
        cls.tomorrow = datetime.date.today() + datetime.datetimedelta(days=1)
        cls.yesterday = datetime.date.today() - datetime.datetimedelta(days=1)

        cls.unassigned_voucher = WorkerVoucher(code=uuid4(), expiry_date=cls.tomorrow, policyholder=cls.policyholder,
                                               status=WorkerVoucher.Status.UNASSIGNED)
        cls.unassigned_voucher.save(username=cls.user.username)

    def test_validate_success(self):
        payload = (
            self.user,
            self.policyholder.code,
            (self.insuree.chf_id,),
            ({'start_date': self.today, 'end_date': self.today},)
        )

        res = validate_assign_vouchers(*payload)
        self.assertTrue(res['success'], res.get('error'))
        self.assertEquals(res['data']['count'], 1)
