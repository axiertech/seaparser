# Korrigering av autonomy-plan: låsdesignen

## Vad planen sa
Problem 2: "Lock-filer är 0 byte och används inkonsekvent ... existens-baserade
lås som kan bli stale". Ändring 2 föreslog att ta bort `ssh-probe-launch.lock`
och `work-launch.lock`.

## Vad koden faktiskt gör
Alla tre lås använder `fcntl.flock(LOCK_EX | LOCK_NB)` – kraschsäkert och
automatiskt släppt vid processdöd. De tomma filerna är bara för att
`open('a')` skapar dem.

- `run.lock` – delas av `run.sh`, `work_session.py` (worker) och
  `ssh_probe.py` (worker). Skyddar själva körningen.
- `ssh-probe-launch.lock` – separat lås för `ssh_probe.py` launch-fas.
- `work-launch.lock` – separat lås för `work_session.py` launch-fas.

## Slutsats
Ändring 2 ska **inte** genomföras. Låsdesignen är korrekt. Det som saknas är
dokumentation av varför tre lås finns, inte konsolidering.
