# Verification

The final acceptance run on Windows with Python 3.14 and PostgreSQL 18.7 executed **54 pytest cases**, all passing in 63.25 seconds. The run included four WTForms deprecation warnings about SelectField tuple choices. The local Bootstrap assets were used in a separate Chromium browser check.

## Reproduce

Install requirements and create an empty database with a name ending in _test, such as courselink_test. The suite needs a trusted local owner with CREATEDB and ownership of newly created schemas. Create the restricted courselink_web role as in the README. In the same private shell, set TEST_OWNER_URL and TEST_DATABASE_URL to the owner and runtime URIs for that same _test database. From the project directory run:

```powershell
.\.venv\Scripts\python -m pytest -q
```

The session creates a randomly named template from the authoritative SQL. Every test clones it into a unique disposable database, closes HTTP/SQL connections and drops its own clone. The suite checks both connection database names before setup. Concurrent tests use a thread barrier and two independent PostgreSQL connections. Tests verify return codes and persisted records. Passwords and signing keys in test fixtures are randomly generated.

## Acceptance outcomes

Every numbered case below passed. The test names in tests/test_acceptance.py contain the corresponding IDs.

| IDs | Observed outcomes |
|---|---|
| T01–T03 | Exactly nine core tables after initialization. Valid student insert succeeds. Invalid department reference fails |
| T04–T08 | Pending signup, unique academic claim, incorrect password denial, pending/disabled/rejected login restrictions and administrator approval all verified |
| T09–T10 | Wrong-role dashboard and unassigned teacher roster/grade requests return 403 |
| T11–T15 | Eligible registration succeeds. Exact duplicate, second section, missing/low prerequisites and full offering return their specified reasons |
| T16 | Simultaneous last-seat requests return one REGISTERED and one OFFERING_FULL. Remaining seats equal zero |
| T17–T18 | Withdrawal creates its event, blocks same-offering reuse, permits an eligible new section and rejects invalid withdrawal |
| T19–T20 | Grading offering 10 with 3.00 changes student 1 GPA to 3.44. Grade 4.10 is rejected |
| T21–T24 | Rolled-back department update is absent. Fixture GPA equals manual 3.70. Grading produces no enrollment event. Dashboard matches query |
| T25–T28 | Completed records count toward capacity. Too-small capacity fails. Disabling invalidates next protected request. Public admin signup fails |
| T29–T31 | Forged student ID cannot affect another student's record. Direct enrollment/audit writes are denied. Rollback removes enrollment and event |
| T32–T34 | Simultaneous section requests and identity claims each have one winner. Unassigned grade correction fails |
| T35–T38 | Missing/invalid CSRF tokens fail. Repeated withdrawal and grading dropped/open records fail. Historical edits and premature completion fail. Empty GPA is NULL |
| T39 | Withdrawal/registration race has a valid serialized outcome with matching occupancy |
| T40 | HTTP workflow covers administration, offering creation/edit/lifecycle, student registration and assigned teacher grading. Additional tests exercise directory writes, rejection, disabling, prerequisite add/remove and post-completion grade correction |

## Browser checks

A Chromium session signed in and out as administrator, student and teacher against the running local application. It opened the account queue, filtered the catalog to the two Database Systems Laboratory sections, and followed an assigned roster link. The catalog was checked at 390 × 844 for document-level horizontal overflow. Wide tables scroll inside their panel. These checks complement the transactional HTTP tests above.
