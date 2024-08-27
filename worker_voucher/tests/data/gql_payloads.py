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
