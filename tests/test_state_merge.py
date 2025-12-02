from core.state import GlobalState

def test_merge_last_writer_wins():
    gs = GlobalState("A")
    gs.update_local(25.0)

    # Incoming older update should be ignored
    old_update = {
        "A": {
            "value": 30.0,
            "timestamp": gs.state["A"].timestamp - 10
        }
    }
    gs.merge(old_update)
    assert gs.state["A"].value == 25.0

    # Incoming newer update should overwrite
    new_update = {
        "A": {
            "value": 28.0,
            "timestamp": gs.state["A"].timestamp + 10
        }
    }
    gs.merge(new_update)
    assert gs.state["A"].value == 28.0

def test_digest_is_deterministic():
    gs = GlobalState("A")
    gs.update_local(25.0)
    digest1 = gs.digest()
    digest2 = gs.digest()
    assert digest1 == digest2
