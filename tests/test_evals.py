from evals.run_evals import TASKS

def test_task_names_are_unique():
    names = [t["name"] for t in TASKS]
    assert len(names) == len(set(names))

def test_every_task_is_well_formed():
    for t in TASKS:
        assert t["task"] and callable(t["check"])
        assert all("/" not in f for f in t["setup"])