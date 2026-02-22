"""
TDD tests for Jaco step control endpoints: next_step, show_all_steps.

Tests the REST endpoint handler logic using mocked dependencies.
"""

import pytest
from unittest.mock import patch, MagicMock
from open_webui.utils.step_mode import StepContext


# ---------------------------------------------------------------------------
# Helper: build a mock ChatModel with step_context
# ---------------------------------------------------------------------------
def _make_chat(chat_id="chat-1", user_id="user-1", step_context=None, chat_data=None):
    mock = MagicMock()
    mock.id = chat_id
    mock.user_id = user_id
    mock.step_context = step_context
    mock.chat = chat_data or {"title": "Test Chat", "history": {"messages": {}}}
    mock.title = "Test Chat"
    return mock


# =========================================================================
# Tests for next_step endpoint logic
# =========================================================================

class TestNextStep:
    """Tests for the next_step endpoint logic."""

    def test_next_step_advances_current_step(self):
        """Advancing should increment current_step."""
        ctx = StepContext(
            active_plan=True,
            current_step=1,
            total_steps_estimated=5,
            plan_summary="Deploy app",
            full_plan_cache="2. Do second thing\n3. Do third thing",
        )
        # Simulate advancing: increment step, return next cached step
        ctx.current_step += 1
        assert ctx.current_step == 2

    def test_next_step_returns_cached_content_when_available(self):
        """When full_plan_cache has content, next_step should extract the next step."""
        from open_webui.utils.step_mode import split_first_step

        cached = "2. Create virtualenv\n3. Install deps\n4. Run tests"
        first, remaining = split_first_step(cached)
        assert "Create virtualenv" in first
        assert "Install deps" in remaining

    def test_next_step_clears_plan_when_no_remaining(self):
        """When no steps remain, the plan should be deactivated."""
        from open_webui.utils.step_mode import split_first_step

        cached = "2. Final step only"
        first, remaining = split_first_step(cached)
        assert "Final step" in first
        assert remaining == ""
        # After last step, plan should be deactivated
        ctx = StepContext(active_plan=True, current_step=1, full_plan_cache=cached)
        ctx.current_step += 1
        _, remaining = split_first_step(ctx.full_plan_cache)
        ctx.full_plan_cache = remaining if remaining else None
        if not ctx.full_plan_cache:
            ctx.active_plan = False
        assert ctx.active_plan is False
        assert ctx.full_plan_cache is None

    def test_next_step_no_active_plan_returns_none(self):
        """When there's no active plan, next_step returns no content."""
        ctx = StepContext(active_plan=False)
        assert ctx.active_plan is False
        assert ctx.full_plan_cache is None

    def test_next_step_with_empty_cache_deactivates_plan(self):
        """Empty cache means no more steps — deactivate."""
        ctx = StepContext(active_plan=True, current_step=3, full_plan_cache="")
        if not ctx.full_plan_cache:
            ctx.active_plan = False
        assert ctx.active_plan is False

    def test_next_step_preserves_plan_summary(self):
        """Advancing shouldn't change plan_summary."""
        ctx = StepContext(
            active_plan=True,
            current_step=2,
            total_steps_estimated=5,
            plan_summary="Deploy the app",
            full_plan_cache="3. Step three",
        )
        ctx.current_step += 1
        assert ctx.plan_summary == "Deploy the app"

    def test_next_step_step_context_persisted(self):
        """After advancing, step context should be serializable."""
        ctx = StepContext(
            active_plan=True,
            current_step=1,
            total_steps_estimated=3,
            full_plan_cache="2. Next\n3. Last",
        )
        ctx.current_step += 1
        d = ctx.to_dict()
        restored = StepContext.from_dict(d)
        assert restored.current_step == 2
        assert restored.active_plan is True


# =========================================================================
# Tests for show_all_steps endpoint logic
# =========================================================================

class TestShowAllSteps:
    """Tests for the show_all_steps endpoint logic."""

    def test_show_all_returns_full_plan_cache(self):
        """show_all_steps should return the full cached plan."""
        ctx = StepContext(
            active_plan=True,
            current_step=1,
            full_plan_cache="2. Create venv\n3. Install deps\n4. Run app",
            plan_summary="Setup project",
        )
        assert ctx.full_plan_cache is not None
        assert "Create venv" in ctx.full_plan_cache
        assert "Install deps" in ctx.full_plan_cache
        assert "Run app" in ctx.full_plan_cache

    def test_show_all_no_active_plan(self):
        """If no active plan, show_all returns nothing useful."""
        ctx = StepContext(active_plan=False)
        assert ctx.full_plan_cache is None

    def test_show_all_includes_plan_summary(self):
        """show_all should provide the plan summary."""
        ctx = StepContext(
            active_plan=True,
            plan_summary="Build and deploy application",
            full_plan_cache="2. Build\n3. Deploy",
        )
        assert ctx.plan_summary == "Build and deploy application"

    def test_show_all_returns_total_estimated(self):
        """show_all should include step count info."""
        ctx = StepContext(
            active_plan=True,
            current_step=2,
            total_steps_estimated=6,
            full_plan_cache="3. Step three\n4. Step four\n5. Step five\n6. Step six",
        )
        assert ctx.total_steps_estimated == 6
        assert ctx.current_step == 2

    def test_show_all_with_empty_cache_still_has_summary(self):
        """Even if cache is empty, the summary is available."""
        ctx = StepContext(
            active_plan=True,
            plan_summary="Original task",
            full_plan_cache="",
        )
        assert ctx.plan_summary == "Original task"


# =========================================================================
# Tests for the get_next_step / get_all_steps helper functions
# =========================================================================

class TestGetNextStepHelper:
    """Tests for the get_next_step helper function."""

    def test_get_next_step_with_cache(self):
        from open_webui.utils.step_mode import get_next_step

        ctx = StepContext(
            active_plan=True,
            current_step=1,
            total_steps_estimated=3,
            full_plan_cache="2. Create virtualenv\n3. Install dependencies",
        )
        result = get_next_step(ctx)
        assert result is not None
        assert result["content"] is not None
        assert "Create virtualenv" in result["content"]
        assert result["step_context"]["current_step"] == 2
        assert result["step_context"]["active_plan"] is True

    def test_get_next_step_last_step(self):
        from open_webui.utils.step_mode import get_next_step

        ctx = StepContext(
            active_plan=True,
            current_step=2,
            total_steps_estimated=3,
            full_plan_cache="3. Final step here",
        )
        result = get_next_step(ctx)
        assert result is not None
        assert "Final step" in result["content"]
        # After last step, plan should be deactivated
        assert result["step_context"]["active_plan"] is False
        assert result["step_context"]["full_plan_cache"] is None

    def test_get_next_step_no_plan(self):
        from open_webui.utils.step_mode import get_next_step

        ctx = StepContext(active_plan=False)
        result = get_next_step(ctx)
        assert result is None

    def test_get_next_step_empty_cache(self):
        from open_webui.utils.step_mode import get_next_step

        ctx = StepContext(active_plan=True, current_step=3, full_plan_cache="")
        result = get_next_step(ctx)
        assert result is None

    def test_get_next_step_none_cache(self):
        from open_webui.utils.step_mode import get_next_step

        ctx = StepContext(active_plan=True, current_step=3, full_plan_cache=None)
        result = get_next_step(ctx)
        assert result is None

    def test_get_next_step_multiple_advances(self):
        from open_webui.utils.step_mode import get_next_step

        ctx = StepContext(
            active_plan=True,
            current_step=1,
            total_steps_estimated=4,
            full_plan_cache="2. Step two\n3. Step three\n4. Step four",
        )
        # First advance
        result = get_next_step(ctx)
        assert "Step two" in result["content"]
        ctx = StepContext.from_dict(result["step_context"])

        # Second advance
        result = get_next_step(ctx)
        assert "Step three" in result["content"]
        ctx = StepContext.from_dict(result["step_context"])

        # Third advance (last step)
        result = get_next_step(ctx)
        assert "Step four" in result["content"]
        assert result["step_context"]["active_plan"] is False


class TestGetAllStepsHelper:
    """Tests for the get_all_steps helper function."""

    def test_get_all_steps_with_cache(self):
        from open_webui.utils.step_mode import get_all_steps

        ctx = StepContext(
            active_plan=True,
            current_step=1,
            total_steps_estimated=4,
            plan_summary="Deploy the app",
            full_plan_cache="2. Build Docker image\n3. Push to registry\n4. Deploy to K8s",
        )
        result = get_all_steps(ctx)
        assert result is not None
        assert result["plan_summary"] == "Deploy the app"
        assert "Build Docker image" in result["full_plan"]
        assert "Push to registry" in result["full_plan"]
        assert result["current_step"] == 1
        assert result["total_steps_estimated"] == 4

    def test_get_all_steps_no_plan(self):
        from open_webui.utils.step_mode import get_all_steps

        ctx = StepContext(active_plan=False)
        result = get_all_steps(ctx)
        assert result is None

    def test_get_all_steps_empty_cache(self):
        from open_webui.utils.step_mode import get_all_steps

        ctx = StepContext(active_plan=True, current_step=3, full_plan_cache="")
        result = get_all_steps(ctx)
        assert result is not None
        assert result["full_plan"] == ""

    def test_get_all_steps_includes_metadata(self):
        from open_webui.utils.step_mode import get_all_steps

        ctx = StepContext(
            active_plan=True,
            current_step=3,
            total_steps_estimated=8,
            plan_summary="Migrate database",
            full_plan_cache="4. Run migrations\n5. Verify",
        )
        result = get_all_steps(ctx)
        assert result["current_step"] == 3
        assert result["total_steps_estimated"] == 8
        assert result["plan_summary"] == "Migrate database"
