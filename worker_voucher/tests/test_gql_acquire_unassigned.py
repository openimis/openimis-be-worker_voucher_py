from django.test import TestCase
from graphene import Schema
from graphene.test import Client

from core.models import Role, MutationLog
from core.test_helpers import create_test_interactive_user
from worker_voucher.models import WorkerVoucher
from worker_voucher.schema import Query, Mutation
from worker_voucher.tests.data.gql_payloads import gql_mutation_acquire_unassigned
from worker_voucher.tests.util import create_test_eu_for_user


class GQLAcquireUnassignedTestCase(TestCase):
    class GQLContext:
        def __init__(self, user):
            self.user = user

    user = None
    eu = None

    gql_client = None
    gql_context = None

    @classmethod
    def setUpClass(cls):
        super(GQLAcquireUnassignedTestCase, cls).setUpClass()

        role_employer = Role.objects.get(name='Employer', validity_to__isnull=True)

        cls.user = create_test_interactive_user(username='VoucherTestUser1', roles=[role_employer.id])
        cls.eu = create_test_eu_for_user(cls.user)

        gql_schema = Schema(
            query=Query,
            mutation=Mutation
        )

        cls.gql_client = Client(gql_schema)
        cls.gql_context = cls.GQLContext(cls.user)

    def test_mutate(self):
        mutation_id = "jgh495hgbn948n54"
        payload = gql_mutation_acquire_unassigned % (
            self.eu.code,
            1,
            mutation_id
        )

        _ = self.gql_client.execute(payload, context=self.gql_context)
        mutation_log = MutationLog.objects.get(client_mutation_id=mutation_id)
        self.assertFalse(mutation_log.error)
        vouchers = WorkerVoucher.objects.filter(policyholder=self.eu, insuree=None)
        self.assertEquals(vouchers.count(), 1)
