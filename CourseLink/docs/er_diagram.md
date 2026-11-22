# CourseLink entity relationships

```mermaid
erDiagram
    DEPARTMENTS ||--o{ STUDENTS : contains
    DEPARTMENTS ||--o{ TEACHERS : employs
    DEPARTMENTS ||--o{ COURSES : owns
    COURSES ||--o{ COURSE_OFFERINGS : schedules
    TEACHERS ||--o{ COURSE_OFFERINGS : teaches
    COURSES ||--o{ PREREQUISITES : requires
    COURSES ||--o{ PREREQUISITES : qualifies
    STUDENTS ||--o{ ENROLLMENTS : registers
    COURSE_OFFERINGS ||--o{ ENROLLMENTS : admits
    ENROLLMENTS ||--o{ ENROLLMENT_AUDIT : records
    STUDENTS o|--o| USERS : claims
    TEACHERS o|--o| USERS : claims
    DEPARTMENTS { int dept_id PK }
    STUDENTS {
        int student_id PK
        int dept_id FK
    }
    TEACHERS {
        int teacher_id PK
        int dept_id FK
    }
    COURSES {
        int course_id PK
        int dept_id FK
    }
    COURSE_OFFERINGS {
        int offering_id PK
        int course_id FK
        int teacher_id FK
    }
    PREREQUISITES {
        int course_id PK,FK
        int prereq_course_id PK,FK
    }
    ENROLLMENTS {
        bigint enrollment_id PK
        int student_id FK
        int offering_id FK
    }
    ENROLLMENT_AUDIT {
        bigint audit_id PK
        bigint enrollment_id FK
    }
    USERS {
        bigint user_id PK
        int student_id FK,UK
        int teacher_id FK,UK
    }
```

Each academic identity can claim at most one account. A student account links to exactly one student, a teacher account to exactly one teacher, and an admin has both foreign keys null. The role check imposes that additional exclusive relationship.
