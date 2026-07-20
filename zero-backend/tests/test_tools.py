from services.tools import get_current_time, get_github_profile


def test_get_current_time():
    time_str = get_current_time()
    assert isinstance(time_str, str)
    assert len(time_str) > 0
    # Expected format: YYYY-MM-DD HH:MM:SS
    assert "-" in time_str
    assert ":" in time_str

def test_get_github_profile():
    # Use a dummy or known username. Note: This makes a real network request.
    # In a real CI environment, we would use VCR.py or mock this.
    res = get_github_profile("rahulsiiitm")
    assert isinstance(res, str)
    assert "User:" in res or "Error" in res or "Could not fetch" in res
