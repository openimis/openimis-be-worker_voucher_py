from insuree.models import Insuree
from policyholder.models import PolicyHolder, PolicyHolderUser, PolicyHolderInsuree


def create_test_eu(user):
    eu = PolicyHolder(
        code='test_eu',
        trade_name='Test EU'
    )
    eu.save(user=user)
    return eu

def create_test_phu(user, eu):
    phu = PolicyHolderUser(
        policy_holder=eu,
        user=user
    )
    phu.save(user=user)
    return phu


def create_test_eu_for_user(user):
    eu = create_test_eu(user)
    _ = create_test_phu(user, eu)
    return eu

def create_test_worker(user, chf_id="2675135421017"):
    worker = Insuree(
        other_names="Test",
        last_name="Insuree",
        chf_id=chf_id,
        audit_user_id=user.id_for_audit
    )
    worker.save()
    return worker

def create_test_phi(user, eu, worker):
    phi = PolicyHolderInsuree(
        policy_holder=eu,
        insuree=worker
    )
    phi.save(user=user)
    return phi


def create_test_worker_for_user_and_eu(user, eu):
    worker = create_test_worker(user)
    _ = create_test_phi(user, eu, worker)
    return worker