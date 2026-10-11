-- Körs först EFTER separat godkännande av databasanslutning.
-- Läsning av identitet/behörigheter, ingen beständig dataändring.
DO $verify$
BEGIN
    IF current_database() <> 'seaparser_test' OR current_user <> 'seaparser_test' THEN
        RAISE EXCEPTION 'Fel testidentitet';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = current_user
        AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolinherit)) THEN
        RAISE EXCEPTION 'Testrollen har för stora rollbehörigheter';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_auth_members WHERE member =
        (SELECT oid FROM pg_roles WHERE rolname = current_user)) THEN
        RAISE EXCEPTION 'Testrollen har oväntat rollmedlemskap';
    END IF;
    IF NOT has_database_privilege(current_user, current_database(), 'CONNECT')
       OR NOT has_database_privilege(current_user, current_database(), 'CREATE')
       OR NOT has_schema_privilege(current_user, 'public', 'USAGE')
       OR NOT has_schema_privilege(current_user, 'public', 'CREATE') THEN
        RAISE EXCEPTION 'Nödvändiga migrationsbehörigheter saknas';
    END IF;
    IF has_database_privilege(current_user, current_database(), 'TEMP') THEN
        RAISE EXCEPTION 'Onödig TEMP-behörighet';
    END IF;
END $verify$;
