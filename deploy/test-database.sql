-- ENDAST DATABASADMINISTRATÖREN, efter separat godkännande.
-- Kör med psql -X --set=ON_ERROR_STOP=1 --file=deploy/test-database.sql
-- mot administratörens underhållsdatabas (postgres), INTE --single-transaction.
-- Förutsätter att seaparser_test (roll och databas) inte finns. Avbryt/granska
-- befintliga objekt i stället för att ta över dem. Inga lösenord i denna fil.
CREATE ROLE seaparser_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOINHERIT NOREPLICATION NOBYPASSRLS;
CREATE DATABASE seaparser_test OWNER seaparser_test TEMPLATE template0;
REVOKE ALL ON DATABASE seaparser_test FROM PUBLIC;
-- Ägarrollen får CREATE/CONNECT för egna migrationer; TEMP behövs inte.
REVOKE TEMPORARY ON DATABASE seaparser_test FROM seaparser_test;
GRANT CONNECT, CREATE ON DATABASE seaparser_test TO seaparser_test;

\connect seaparser_test
REVOKE ALL ON SCHEMA public FROM PUBLIC;
-- Migrationshistoriken ligger i public; produktens schema skapas av baslinjen.
GRANT USAGE, CREATE ON SCHEMA public TO seaparser_test;

-- Administratören sätter lösenord separat i interaktiv psql:
-- SET password_encryption = 'scram-sha-256';
-- \password seaparser_test
-- Ge aldrig testrollen medlemskap i seaparser eller andra roller.
-- Ingen ändring av utvecklingsdatabasens PUBLIC-behörigheter görs här.
-- Installera även test-pg_hba.conf.example FÖRE bredare regler; det nekar
-- testrollen åtkomst till andra databaser även om PUBLIC har CONNECT där.
