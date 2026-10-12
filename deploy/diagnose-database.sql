BEGIN READ ONLY;
SELECT current_database() AS database, current_user AS role,
       current_setting('server_version') AS server_version,
       current_setting('transaction_read_only') AS read_only;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolinherit, rolreplication, rolbypassrls
FROM pg_roles WHERE rolname = current_user;
SELECT p.rolname AS granted_role
FROM pg_auth_members m JOIN pg_roles p ON p.oid = m.roleid
WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = current_user);
SELECT datname, pg_get_userbyid(datdba) AS owner,
       has_database_privilege(current_user, oid, 'CONNECT') AS connect,
       has_database_privilege(current_user, oid, 'CREATE') AS create,
       has_database_privilege(current_user, oid, 'TEMP') AS temp
FROM pg_database WHERE datname = current_database();
SELECT extname, extversion FROM pg_extension WHERE extname LIKE 'postgis%';
SELECT nspname, has_schema_privilege(current_user, oid, 'USAGE') AS usage,
       has_schema_privilege(current_user, oid, 'CREATE') AS create
FROM pg_namespace WHERE nspname IN ('public', 'seaparser');
SELECT schemaname, tablename,
       has_table_privilege(current_user, format('%I.%I', schemaname, tablename), 'SELECT') AS select,
       has_table_privilege(current_user, format('%I.%I', schemaname, tablename), 'INSERT') AS insert,
       has_table_privilege(current_user, format('%I.%I', schemaname, tablename), 'UPDATE') AS update,
       has_table_privilege(current_user, format('%I.%I', schemaname, tablename), 'DELETE') AS delete
FROM pg_tables WHERE schemaname IN ('public', 'seaparser');
ROLLBACK;
