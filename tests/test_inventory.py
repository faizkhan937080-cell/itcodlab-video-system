from scripts import inventory as I


def test_inventory_lists_owned_tools_and_flags_missing_3d():
    out = I.render()
    assert "remotion" in out and "ltx=" in out and "Zoom/pan on stills" in out
    assert ("NOT installed" in out) == (not I.facts()["three_in_remotion"])
