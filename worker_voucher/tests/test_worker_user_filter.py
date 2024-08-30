from django.test import TestCase

from core.models import Role
from core.test_helpers import create_test_interactive_user
from insuree.models import Insuree
from insuree.test_helpers import generate_random_insuree_number
from worker_voucher.services import worker_user_filter
from worker_voucher.tests.util import create_test_eu_for_user, create_test_worker_for_eu, create_test_eu


class WorkerQueryTestCase(TestCase):
    user_admin = None
    user_inspector = None
    user_employer = None

    eu = None
    eu2 = None
    eu3 = None

    worker = None
    worker2 = None
    worker3 = None
    worker4 = None

    @classmethod
    def setUpClass(cls):
        super(WorkerQueryTestCase, cls).setUpClass()

        role_admin = Role.objects.get(name='IMIS Administrator', validity_to__isnull=True)
        role_inspector = Role.objects.get(name='Inspector', validity_to__isnull=True)
        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username="TestEmployer", roles=[role_employer.id])
        cls.user_inspector = create_test_interactive_user(username="TestInspector", roles=[role_inspector.id])
        cls.user_admin = create_test_interactive_user(username="TestAdmin", roles=[role_admin.id])

        cls.eu = create_test_eu_for_user(cls.user, code="test_eu1")
        cls.eu2 = create_test_eu_for_user(cls.user, code="test_eu2")
        cls.eu3 = create_test_eu(cls.user, code="test_eu3")  # eu not assigned to any user
        cls.worker = create_test_worker_for_eu(cls.user, cls.eu, chf_id=f"{generate_random_insuree_number()}")
        cls.worker2 = create_test_worker_for_eu(cls.user, cls.eu2, chf_id=f"{generate_random_insuree_number()}")
        cls.worker3 = create_test_worker_for_eu(cls.user, cls.eu2, chf_id=f"{generate_random_insuree_number()}")
        cls.worker4 = create_test_worker_for_eu(cls.user, cls.eu3, chf_id=f"{generate_random_insuree_number()}")

    def test_query_admin(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_admin, None)).count()
        self.assertEquals(worker_count, 64)  # 60 from demo + 4 test

    def test_query_admin_eu1(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_admin, self.eu.code)).count()
        self.assertEquals(worker_count, 1)

    def test_query_admin_eu2(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_admin, self.eu2.code)).count()
        self.assertEquals(worker_count, 2)

    def test_query_admin_eu3(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_admin, self.eu3.code)).count()
        self.assertEquals(worker_count, 1)

    def test_query_inspector(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_inspector, None)).count()
        self.assertEquals(worker_count, 64)  # 60 from demo + 4 test

    def test_query_inspector_eu(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_inspector, self.eu.code)).count()
        self.assertEquals(worker_count, 1)

    def test_query_inspector_eu2(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_inspector, self.eu2.code)).count()
        self.assertEquals(worker_count, 2)

    def test_query_inspector_eu3(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user_inspector, self.eu3.code)).count()
        self.assertEquals(worker_count, 1)

    def test_query_employer(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user, None)).count()
        self.assertEquals(worker_count, 3)

    def test_query_employer_eu(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user, self.eu.code)).count()
        self.assertEquals(worker_count, 1)

    def test_query_employer_eu2(self):
        worker_count = Insuree.objects.filter(worker_user_filter(self.user, self.eu2.code)).count()
        self.assertEquals(worker_count, 2)

    def test_query_employer_eu3(self):
        # EU not assigned to user, should not return workers
        worker_count = Insuree.objects.filter(worker_user_filter(self.user, self.eu3.code)).count()
        self.assertEquals(worker_count, 0)
