from pressready import spine_width_in


def test_spine_cream():
    assert spine_width_in(284, "cream") == 0.71


def test_spine_white():
    assert spine_width_in(229, "white") == 0.5157
