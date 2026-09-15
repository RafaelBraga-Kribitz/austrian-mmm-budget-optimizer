"""Theme wrapper must call bk_theme.apply with the positional theme name."""

from ambo.plots.theme import apply_theme, channel_colors, tokens


def test_apply_theme_does_not_raise():
    apply_theme()
    assert tokens()["accent-01"] == "#FA6400"
    assert len(channel_colors(5)) == 5
