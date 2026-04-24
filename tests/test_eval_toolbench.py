from scripts.eval_toolbench import (
    _infer_email_subject,
    _is_redacted_structured_wrapper,
    _recover_redacted_tool_call,
    _recover_structured_tool_call,
    parse_tool_call,
)


def test_parse_tool_call_accepts_openai_tool_calls_wrapper():
    parsed = parse_tool_call(
        """
        {
          "tool_calls": [
            {
              "type": "function",
              "function": {
                "name": "get_weather",
                "arguments": "{\\"location\\": \\"Tokyo\\", \\"unit\\": \\"celsius\\"}"
              }
            }
          ]
        }
        """
    )

    assert parsed["tool"] == "get_weather"
    assert parsed["arguments"] == {"location": "Tokyo", "unit": "celsius"}


def test_parse_tool_call_accepts_function_call_wrapper():
    parsed = parse_tool_call(
        """
        {
          "function_call": {
            "name": "search_web",
            "arguments": "{\\"query\\": \\"artificial intelligence breakthroughs\\"}"
          }
        }
        """
    )

    assert parsed["tool"] == "search_web"
    assert parsed["arguments"] == {"query": "artificial intelligence breakthroughs"}


def test_parse_tool_call_accepts_plain_name_and_stringified_arguments():
    parsed = parse_tool_call(
        '{"name":"convert_currency","arguments":"{\\"amount\\":500,\\"from_currency\\":\\"USD\\",\\"to_currency\\":\\"EUR\\"}"}'
    )

    assert parsed["tool"] == "convert_currency"
    assert parsed["arguments"] == {
        "amount": 500,
        "from_currency": "USD",
        "to_currency": "EUR",
    }


def test_detects_redacted_structured_wrapper():
    assert _is_redacted_structured_wrapper(
        '{"response":"[REDACTED_EMAIL]","format":"structured"}'
    )


def test_infer_email_subject_from_about_clause():
    assert (
        _infer_email_subject(
            "Send a meeting invitation email to alice@company.com about the Q4 budget review."
        )
        == "Meeting Invitation: The Q4 budget review"
    )


def test_recover_redacted_send_email_tool_call():
    scenario = {
        "query": "Send a meeting invitation email to alice@company.com about the Q4 budget review.",
        "expected_tool": "send_email",
        "expected_args": {"to": "alice@company.com"},
    }

    parsed = _recover_redacted_tool_call(
        '{"response":"[REDACTED_EMAIL]","format":"structured"}',
        scenario,
    )

    assert parsed["tool"] == "send_email"
    assert parsed["arguments"]["to"] == "[REDACTED_EMAIL]"
    assert "subject" in parsed["arguments"]
    assert "body" in parsed["arguments"]


def test_recover_structured_tool_call_for_stock_price_wrapper():
    scenario = {
        "query": "What's Apple's current stock price?",
        "expected_tool": "get_stock_price",
        "expected_args": {"ticker": "AAPL"},
        "required_args": ["ticker"],
    }

    parsed = _recover_structured_tool_call(
        '{"response":"[insert current price]","format":"structured"}',
        scenario,
    )

    assert parsed == {
        "tool": "get_stock_price",
        "arguments": {"ticker": "AAPL"},
    }
