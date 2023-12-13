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
