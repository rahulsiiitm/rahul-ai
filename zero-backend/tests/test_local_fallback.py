from models.schemas import Message
from services.local_fallback import build_local_fallback


def response_for(text: str) -> str:
    return build_local_fallback([Message(role="user", content=text)])


def test_identity_fallback_describes_zero_not_rahul():
    response = response_for("who are u??")
    assert "I'm Zero" in response
    assert "AI co-pilot" in response


def test_chief_fallback_uses_portfolio_facts():
    response = response_for("Who is Rahul?")
    assert "IIIT Manipur" in response
    assert "SUTRA" in response


def test_unknown_fallback_never_claims_total_outage():
    response = response_for("Tell me something unusual")
    assert "upstream providers are unavailable" not in response.lower()
    assert "projects" in response.lower()


def test_substrings_do_not_trigger_greetings():
    response = response_for("Something technical")
    assert not response.startswith("Hey.")


def test_informal_identity_question_is_supported():
    assert "I'm Zero" in response_for("what are u btw?")
