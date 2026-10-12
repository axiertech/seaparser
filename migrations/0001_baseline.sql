-- Endast projektets migrationshistorik; inga befintliga objekt ändras.
CREATE TABLE public.seaparser_migrations (
    version text PRIMARY KEY,
    checksum text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);
