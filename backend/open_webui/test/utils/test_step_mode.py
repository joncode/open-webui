import pytest
from open_webui.utils.step_mode import (
    StepContext,
    STEP_MODE_SYSTEM_PROMPT,
    extract_step_metadata,
    strip_step_metadata,
    detect_multi_step_leak,
    split_first_step,
    is_advance_request,
    is_full_plan_request,
    inject_step_system_prompt,
)


class TestStepContext:
    """Tests for StepContext dataclass and serialization."""

    def test_default_values(self):
        ctx = StepContext()
        assert ctx.active_plan is False
        assert ctx.total_steps_estimated == 0
        assert ctx.current_step == 0
        assert ctx.plan_summary == ""
        assert ctx.full_plan_cache is None
        assert ctx.step_mode_enabled is True

    def test_custom_values(self):
        ctx = StepContext(
            active_plan=True,
            total_steps_estimated=5,
            current_step=3,
            plan_summary="Deploy app",
            full_plan_cache="cached steps",
            step_mode_enabled=False,
        )
        assert ctx.active_plan is True
        assert ctx.total_steps_estimated == 5
        assert ctx.current_step == 3
        assert ctx.plan_summary == "Deploy app"
        assert ctx.full_plan_cache == "cached steps"
        assert ctx.step_mode_enabled is False

    def test_to_dict(self):
        ctx = StepContext(active_plan=True, current_step=2, plan_summary="test")
        d = ctx.to_dict()
        assert d == {
            "active_plan": True,
            "total_steps_estimated": 0,
            "current_step": 2,
            "plan_summary": "test",
            "full_plan_cache": None,
            "step_mode_enabled": True,
        }

    def test_from_dict_roundtrip(self):
        original = StepContext(
            active_plan=True,
            total_steps_estimated=10,
            current_step=7,
            plan_summary="Migrate database",
            full_plan_cache="step 8\nstep 9\nstep 10",
            step_mode_enabled=False,
        )
        d = original.to_dict()
        restored = StepContext.from_dict(d)
        assert restored.active_plan == original.active_plan
        assert restored.total_steps_estimated == original.total_steps_estimated
        assert restored.current_step == original.current_step
        assert restored.plan_summary == original.plan_summary
        assert restored.full_plan_cache == original.full_plan_cache
        assert restored.step_mode_enabled == original.step_mode_enabled

    def test_from_dict_none(self):
        ctx = StepContext.from_dict(None)
        assert ctx.active_plan is False
        assert ctx.step_mode_enabled is True

    def test_from_dict_empty(self):
        ctx = StepContext.from_dict({})
        assert ctx.active_plan is False
        assert ctx.step_mode_enabled is True

    def test_from_dict_partial(self):
        ctx = StepContext.from_dict({"active_plan": True, "current_step": 5})
        assert ctx.active_plan is True
        assert ctx.current_step == 5
        assert ctx.total_steps_estimated == 0
        assert ctx.plan_summary == ""

    def test_from_dict_extra_keys_ignored(self):
        ctx = StepContext.from_dict({"active_plan": True, "unknown_field": "value"})
        assert ctx.active_plan is True


class TestExtractStepMetadata:
    """Tests for extract_step_metadata."""

    def test_valid_metadata(self):
        response = 'Do this thing.\n<!-- jaco-step: {"current": 1, "total_estimated": 5, "plan_summary": "setup"} -->'
        result = extract_step_metadata(response)
        assert result == {"current": 1, "total_estimated": 5, "plan_summary": "setup"}

    def test_no_metadata(self):
        result = extract_step_metadata("Just a normal response with no metadata.")
        assert result is None

    def test_invalid_json_in_metadata(self):
        response = "<!-- jaco-step: {not valid json} -->"
        result = extract_step_metadata(response)
        assert result is None

    def test_metadata_in_middle_of_response(self):
        response = 'Some text\n<!-- jaco-step: {"current": 3, "total_estimated": 10} -->\nMore text'
        result = extract_step_metadata(response)
        assert result == {"current": 3, "total_estimated": 10}

    def test_metadata_with_extra_whitespace(self):
        response = '<!--  jaco-step:  {"current": 1}  -->'
        result = extract_step_metadata(response)
        assert result == {"current": 1}

    def test_empty_string(self):
        assert extract_step_metadata("") is None

    def test_multiline_metadata(self):
        response = '<!-- jaco-step: {\n"current": 1,\n"total_estimated": 3\n} -->'
        result = extract_step_metadata(response)
        assert result == {"current": 1, "total_estimated": 3}


class TestStripStepMetadata:
    """Tests for strip_step_metadata."""

    def test_strip_metadata_at_end(self):
        response = 'Do this thing.\n<!-- jaco-step: {"current": 1} -->'
        result = strip_step_metadata(response)
        assert result == "Do this thing."

    def test_strip_metadata_in_middle(self):
        response = 'Before\n<!-- jaco-step: {"current": 1} -->\nAfter'
        result = strip_step_metadata(response)
        assert result == "Before\n\nAfter"

    def test_no_metadata_to_strip(self):
        response = "Just a plain response."
        assert strip_step_metadata(response) == "Just a plain response."

    def test_empty_string(self):
        assert strip_step_metadata("") == ""

    def test_strips_trailing_whitespace(self):
        response = 'Text.\n<!-- jaco-step: {"current": 1} -->  \n  '
        result = strip_step_metadata(response)
        assert result == "Text."


class TestDetectMultiStepLeak:
    """Tests for detect_multi_step_leak."""

    def test_numbered_list_three_items(self):
        response = "1. Install Python\n2. Create virtualenv\n3. Install dependencies"
        assert detect_multi_step_leak(response) is True

    def test_numbered_list_with_step_prefix(self):
        response = "Step 1. Do this\nStep 2. Do that\nStep 3. Finish"
        assert detect_multi_step_leak(response) is True

    def test_numbered_list_with_parens(self):
        response = "1) First thing\n2) Second thing\n3) Third thing"
        assert detect_multi_step_leak(response) is True

    def test_first_second_pattern(self):
        response = "First, install the package. Then do some config. Second, configure the settings."
        assert detect_multi_step_leak(response) is True

    def test_step_1_step_2_pattern(self):
        response = "Step 1: Install Node.js and make sure it works. Step 2: Run the build."
        assert detect_multi_step_leak(response) is True

    def test_single_step_response(self):
        response = "Install Python by running `brew install python`."
        assert detect_multi_step_leak(response) is False

    def test_single_numbered_item(self):
        response = "1. Just one item here."
        assert detect_multi_step_leak(response) is False

    def test_two_numbered_items_not_enough(self):
        # The regex requires 3+ numbered items (1 initial + 2 more)
        response = "1. First thing\n2. Second thing"
        assert detect_multi_step_leak(response) is False

    def test_empty_string(self):
        assert detect_multi_step_leak("") is False

    def test_numbered_list_with_content_between(self):
        response = "Here's what to do:\n1. Install Python\nMake sure it's 3.10+\n2. Create venv\n3. Activate"
        assert detect_multi_step_leak(response) is True


class TestSplitFirstStep:
    """Tests for split_first_step."""

    def test_basic_split(self):
        response = "1. Install Python\n2. Create virtualenv\n3. Install deps"
        first, remaining = split_first_step(response)
        assert "Install Python" in first
        assert "Create virtualenv" in remaining
        assert "Install deps" in remaining

    def test_single_step(self):
        response = "Just do this one thing."
        first, remaining = split_first_step(response)
        assert first == "Just do this one thing."
        assert remaining == ""

    def test_first_step_with_intro(self):
        response = "Here's what to do:\n1. Install Python\n2. Create venv\n3. Run it"
        first, remaining = split_first_step(response)
        assert "Here's what to do:" in first
        assert "Install Python" in first
        assert "Create venv" in remaining

    def test_empty_string(self):
        first, remaining = split_first_step("")
        assert first == ""
        assert remaining == ""

    def test_step_prefix_format(self):
        response = "Step 1. Download the file\nStep 2. Unzip it\nStep 3. Run setup"
        first, remaining = split_first_step(response)
        assert "Download the file" in first
        assert "Unzip it" in remaining

    def test_preserves_content_within_first_step(self):
        response = "1. Install Python\n   Make sure version >= 3.10\n   Check with python --version\n2. Next step"
        first, remaining = split_first_step(response)
        assert "Make sure version >= 3.10" in first
        assert "Check with python --version" in first
        assert "Next step" in remaining


class TestIsAdvanceRequest:
    """Tests for is_advance_request."""

    @pytest.mark.parametrize(
        "msg",
        [
            "next",
            "Next",
            "NEXT",
            "continue",
            "go on",
            "next step",
            "what's next",
            "done",
            "ok next",
            "okay next",
            "proceed",
            "and then",
            "what now",
            "now what",
        ],
    )
    def test_advance_phrases(self, msg):
        assert is_advance_request(msg) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "next",       # with trailing space
            "  next  ",   # with surrounding whitespace
            "next?",      # with question mark
            "next!",      # with exclamation
            "next.",      # with period
        ],
    )
    def test_advance_with_punctuation_and_whitespace(self, msg):
        assert is_advance_request(msg) is True

    def test_not_advance_generic_question(self):
        assert is_advance_request("How do I install Python?") is False

    def test_not_advance_empty(self):
        assert is_advance_request("") is False

    def test_not_advance_partial_match(self):
        assert is_advance_request("next please do something else") is False


class TestIsFullPlanRequest:
    """Tests for is_full_plan_request."""

    @pytest.mark.parametrize(
        "msg",
        [
            "show all steps",
            "full plan",
            "all steps",
            "show me everything",
            "give me all",
            "the whole plan",
            "list all steps",
            "show everything",
            "show all",
        ],
    )
    def test_full_plan_phrases(self, msg):
        assert is_full_plan_request(msg) is True

    def test_full_plan_with_extra_words(self):
        assert is_full_plan_request("can you show all steps please") is True

    def test_full_plan_case_insensitive(self):
        assert is_full_plan_request("SHOW ALL STEPS") is True

    def test_not_full_plan_generic(self):
        assert is_full_plan_request("What should I do?") is False

    def test_not_full_plan_empty(self):
        assert is_full_plan_request("") is False


class TestInjectStepSystemPrompt:
    """Tests for inject_step_system_prompt."""

    def test_inject_no_existing_system_message(self):
        messages = [{"role": "user", "content": "Help me deploy"}]
        ctx = StepContext()
        result = inject_step_system_prompt(messages, ctx)
        assert result[0]["role"] == "system"
        assert STEP_MODE_SYSTEM_PROMPT in result[0]["content"]
        assert result[1]["role"] == "user"

    def test_inject_with_existing_system_message(self):
        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Help me"},
        ]
        ctx = StepContext()
        result = inject_step_system_prompt(messages, ctx)
        assert len(result) == 2
        assert "You are helpful." in result[0]["content"]
        assert STEP_MODE_SYSTEM_PROMPT in result[0]["content"]

    def test_inject_with_active_plan(self):
        messages = [{"role": "user", "content": "next"}]
        ctx = StepContext(
            active_plan=True,
            current_step=3,
            total_steps_estimated=8,
            plan_summary="Deploy the app",
        )
        result = inject_step_system_prompt(messages, ctx)
        system_content = result[0]["content"]
        assert "step 3" in system_content
        assert "~8" in system_content
        assert "Deploy the app" in system_content

    def test_inject_disabled_step_mode(self):
        messages = [{"role": "user", "content": "Hello"}]
        ctx = StepContext(step_mode_enabled=False)
        result = inject_step_system_prompt(messages, ctx)
        # Should return messages unchanged
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_inject_empty_messages(self):
        messages = []
        ctx = StepContext()
        result = inject_step_system_prompt(messages, ctx)
        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_inject_mutates_input_list(self):
        """inject_step_system_prompt modifies the input list in-place and returns it."""
        messages = [{"role": "user", "content": "Hi"}]
        ctx = StepContext()
        result = inject_step_system_prompt(messages, ctx)
        assert result is messages
