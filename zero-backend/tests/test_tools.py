from services.tools import get_current_time, get_github_profile


class FakeResponse:
    status_code = 200

    @staticmethod
    def json():
        return {
            "login": "rahulsiiitm",
            "name": "Rahul",
            "public_repos": 10,
            "followers": 20,
            "bio": "Builder",
        }


def test_get_current_time():
    time_str = get_current_time()
    assert isinstance(time_str, str)
    assert len(time_str) > 0
    # Expected format: YYYY-MM-DD HH:MM:SS
    assert "-" in time_str
    assert ":" in time_str

def test_get_github_profile(monkeypatch):
    monkeypatch.setattr("services.tools.httpx.get", lambda *args, **kwargs: FakeResponse())
    res = get_github_profile("rahulsiiitm")
    assert "User: rahulsiiitm" in res


def test_get_github_profile_rejects_invalid_username():
    assert get_github_profile("../../admin") == "Invalid GitHub username."
