from app.models.playbook import TopicRule
from app.playbook.topic_rules import DEFAULT_TOPICS, get_topic_rules, reset_topic_rules, save_topic_rules


def test_get_topic_rules_returns_defaults_when_unset():
    rules = get_topic_rules()
    assert [r.topic for r in rules] == [r.topic for r in DEFAULT_TOPICS]
    assert any(r.topic == "Payment Terms" for r in rules)


def test_save_topic_rules_persists_and_overrides_defaults():
    custom = [TopicRule(topic="Custom Topic", patterns=[r"\bcustom\b"])]
    save_topic_rules(custom)

    fetched = get_topic_rules()
    assert len(fetched) == 1
    assert fetched[0].topic == "Custom Topic"
    assert fetched[0].patterns == [r"\bcustom\b"]


def test_reset_topic_rules_restores_defaults():
    save_topic_rules([TopicRule(topic="Custom Topic", patterns=[r"\bcustom\b"])])
    reset_topic_rules()

    fetched = get_topic_rules()
    assert [r.topic for r in fetched] == [r.topic for r in DEFAULT_TOPICS]
