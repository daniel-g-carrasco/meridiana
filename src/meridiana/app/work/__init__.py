"""The heavy jobs, one mechanism for all of them (R598, docs/studio/48-lavori-pesanti.md): a job runs in a process of its
own (or a thread, for what only waits), with a ceiling of memory, results on the way, its progress with the time left,
Cancel, and what to do when the project changes under it. `job` (Kind, Handle, Context, mine), `center` (Center, the
one owner of the jobs), `runner` and `worker` (the processes), `wire` (the messages on their pipes), `eta` (the time
left), `store` (the results kept on disk), `sample` (a job for the tests and the guard). Without Qt: the window's
bridge is gui/backend/work.py."""
