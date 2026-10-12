# Granskade Actions-revisioner 2026-10-12

Workflow checks.yml låser samtliga externa actions till fullständiga 40-teckens
commit-SHA. Samma huvudversioner behålls; inga nya tjänster eller CI-jobb införs.

| Action | Release | Fullständig SHA |
| --- | --- | --- |
| actions/checkout | v4.3.1 | 34e114876b0b11c390a56381ad16ebd13914f8d5 |
| actions/setup-python | v5.6.0 | a26af69be951a213d495a4c3e4e4022e16d87065 |
| actions/setup-node | v4.4.0 | 49933ea5288caeca8642d1e84afbd3f7d6820020 |

Officiella releases och deras commitlänkar verifierades. Releaseanteckningar,
commitdiffar och action.yml på exakt respektive SHA lästes. Alla använder Node 20
som actionruntime; workflowens programversioner Python 3.14.4 och Node 22.22.1
behålls. checkout har persist-credentials=false och GITHUB_TOKEN har contents: read.
Setup-actions har cache avstängt som standard; ingen cache eller extra token anges.
Ubuntu 24.04 är fortsatt GitHub-hostad runner, ingen åtkomst till serverkonfiguration.

checkout-revisionen omfattar städning av autentiseringskonfiguration. Python-
releasen innehåller workflow-/semver- och testberoendeändringar. Node-releasen
innehåller matcher-, spegel- och cachebiblioteksändringar. Detta är en avgränsad
proveniens-/konfigurations-/kompatibilitetsgranskning, inte en fullständig granskning
av bundlad JavaScript eller transitiva beroenden. Ingen faktisk Actions-körning
eller versionstillgänglighet i runner har verifierats. SHA-låsning förhindrar att
en flyttad release-tagg ändrar den valda koden; den ersätter inte framtida granskning.

scripts/check.py avvisar externa uses-referenser utan fullständig SHA offline.
Framtida uppdateringar kräver samma granskning, dokumentation och lokala kontroller.
Push/aktivering kräver användarens godkännande.

Officiella källor:

- [checkout-release](https://github.com/actions/checkout/releases/tag/v4.3.1),
  [commit](https://github.com/actions/checkout/commit/34e114876b0b11c390a56381ad16ebd13914f8d5),
  [action.yml](https://raw.githubusercontent.com/actions/checkout/34e114876b0b11c390a56381ad16ebd13914f8d5/action.yml).
- [setup-python-release](https://github.com/actions/setup-python/releases/tag/v5.6.0),
  [commit](https://github.com/actions/setup-python/commit/a26af69be951a213d495a4c3e4e4022e16d87065),
  [action.yml](https://raw.githubusercontent.com/actions/setup-python/a26af69be951a213d495a4c3e4e4022e16d87065/action.yml).
- [setup-node-release](https://github.com/actions/setup-node/releases/tag/v4.4.0),
  [commit](https://github.com/actions/setup-node/commit/49933ea5288caeca8642d1e84afbd3f7d6820020),
  [action.yml](https://raw.githubusercontent.com/actions/setup-node/49933ea5288caeca8642d1e84afbd3f7d6820020/action.yml).
- [GitHubs säkerhetsinstruktioner för Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions).
