gql_mutation_acquire_assigned = """
mutation acquireAssigned {
  acquireAssignedVouchers(input: {
    economicUnitCode: "%s",
    workers: ["%s"]
    dateRanges: [
      {
        startDate: "%s", 
        endDate: "%s"
      }
    ],
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_acquire_unassigned = """
mutation acquireUnassigned {
  acquireUnassignedVouchers(input: {
    economicUnitCode: "%s",
    count: %s,
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_assign = """
mutation assignVouchers {
  assignVouchers(input: {
    economicUnitCode: "%s",
    workers: ["%s"]
    dateRanges: [
      {
        startDate: "%s", 
        endDate: "%s"
      }
    ],
    clientMutationId: "%s"    
  }) {
    clientMutationId
  }
}
"""

gql_mutation_create_worker = """
mutation createWorker {
  createWorker(input: {
    chfId: "%s",
    lastName: "%s",
    otherNames: "%s",
    genderId: "%s",
    dob: "%s",
    economicUnitCode: "%s",
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_worker_delete = """
mutation deleteWorker {
  deleteWorker(input: {
    uuid: "%s"
    economicUnitCode: "%s"
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_create_group_of_worker = """
mutation addGroupOfWorker {
  createOrUpdateGroupOfWorkers(input: {
    insureesChfId: ["%s"],
    economicUnitCode: "%s",
    name: "%s",
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_create_group_of_worker_empty = """
mutation addGroupOfWorker {
  createOrUpdateGroupOfWorkers(input: {
    insureesChfId: [],
    economicUnitCode: "%s",
    name: "%s",
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_update_group_of_worker_multiple = """
mutation updateGroupOfWorker {
  createOrUpdateGroupOfWorkers(input: {
    id: "%s",
    insureesChfId: ["%s", "%s"],
    economicUnitCode: "%s",
    name: "%s",
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_update_group_of_worker_single = """
mutation updateGroupOfWorker {
  createOrUpdateGroupOfWorkers(input: {
    id: "%s",
    insureesChfId: ["%s"],
    economicUnitCode: "%s",
    name: "%s",
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""

gql_mutation_group_of_worker_delete = """
mutation deleteGroupOfWorker {
  deleteGroupOfWorkers(input: {
    uuid: "%s"
    economicUnitCode: "%s"
    clientMutationId: "%s"
  }) {
    clientMutationId
  }
}
"""
