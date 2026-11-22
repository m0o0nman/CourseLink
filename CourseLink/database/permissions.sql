-- Run as the installation owner after creating the courselink_web login.
BEGIN;
GRANT USAGE ON SCHEMA public TO courselink_web;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO courselink_web;
GRANT INSERT,UPDATE ON departments,students,teachers,courses,course_offerings,prerequisites TO courselink_web;
GRANT DELETE ON prerequisites TO courselink_web;
GRANT INSERT(email,password_hash,role,student_id,teacher_id),UPDATE(status) ON users TO courselink_web;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO courselink_web;
GRANT EXECUTE ON FUNCTION register_student(integer,integer),withdraw_student(integer,integer),submit_grade(integer,bigint,numeric) TO courselink_web;
COMMIT;
