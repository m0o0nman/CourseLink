# Implementation decisions

| Requirement or ambiguity | Adopted decision | Alternative considered and consequence |
|---|---|---|
| Capacity after grading | Enrolled and completed rows occupy seats | Counting only active enrollments would release seats when a grade is entered |
| Dropped registration | Retain the record and disallow reuse of its exact offering | Deletion would lose history. A different section stays eligible |
| Conflicting section registrations | Student lock before offering lock under READ COMMITTED | Offering-only locking would allow a student to take two sections concurrently |
| GPA and empty history | Round a credit-weighted overall demo GPA to two decimals. Return NULL without graded credits | Zero would imply a graded result |
| Offering and course corrections | Freeze identifying offering fields after any enrollment, including teacher assignment. Freeze credits and course code on used courses | Freely editing history could change GPA or transfer grading authority |
| Academic timetable | Use Spring, Summer and Fall as fixture labels | Official calendar integration requires verified institutional policy |
| Identity verification | Pending claim plus administrator comparison with the fictional academic roster and independent classroom confirmation | An ID alone would establish too little evidence |
| Privileged operations | Owner installs and bootstraps, web login gets narrow enrollment routines | Direct table writes would permit registration bypass |
| Grade corrections | Assigned teacher may correct closed or completed results | Separate admin grade correction is optional and omitted |
| Demo users | Generate credentials locally in an owner-only transaction | Shared published passwords would expose demo accounts |
