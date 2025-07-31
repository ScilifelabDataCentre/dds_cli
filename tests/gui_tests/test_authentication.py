"""Focused GUI Authentication tests - UI behavior only."""

from unittest.mock import MagicMock, patch

import pytest

from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.authentication.modals.login_modal import LoginModal
from dds_cli.dds_gui.pages.authentication.modals.logout_modal import LogoutModal
from dds_cli.dds_gui.pages.authentication.modals.reauthenticate_modal import ReAuthenticateModal


# =================================================================================
# Core UI State Management Tests
# =================================================================================


@pytest.mark.asyncio
async def test_auth_status_ui_switching() -> None:
    """Test that UI components change correctly when authentication status changes."""

    app = DDSApp(token_path="test_path")

    async with app.run_test() as pilot:
        # Test not authenticated state
        app.set_auth_status(False)
        await pilot.pause()

        switcher = app.query_one("#auth-status-switcher")
        assert switcher.current == "auth-status-invalid-container"
        assert len(app.query("#login")) > 0, "Login button should be available"

        # Test authenticated state
        app.set_auth_status(True)
        await pilot.pause()

        switcher = app.query_one("#auth-status-switcher")
        assert switcher.current == "auth-status-ok-container"
        assert len(app.query("#logout")) > 0, "Logout button should be available"
        assert len(app.query("#re-authenticate")) > 0, "Re-auth button should be available"


# =================================================================================
# Modal UI Interaction Tests
# =================================================================================


@pytest.mark.asyncio
async def test_login_modal_ui_workflow() -> None:
    """Test 2FA UI workflow: form switching and field appearance."""

    with patch("dds_cli.dds_gui.pages.authentication.authentication_form.Auth") as mock_auth_class:
        mock_auth_instance = MagicMock()
        mock_auth_class.return_value = mock_auth_instance
        mock_auth_instance.login.return_value = ("partial_token_456", "TOTP")
        mock_auth_instance.confirm_twofactor.return_value = None

        app = DDSApp(token_path="test_path")

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(
                login_modal
            )  # Need to manually push the screen, probelm with Textual test runner
            await pilot.pause()

            # Verify modal displayed
            assert len(app.screen_stack) > 1, "Login modal should be displayed"

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            assert username_inputs.first().value == "test_user"
            assert password_inputs.first().value == "test_password"

            # UI Workflow Test: Click "Send 2FA code" triggers form switch
            send_2fa_buttons = app.query("Button#send-2fa-code")

            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # UI Verification: 2FA form should now be displayed
            code_inputs = app.query("Input#code")

            # Test 2FA field interaction
            code_inputs.first().value = "123456"
            await pilot.pause()

            assert code_inputs.first().value == "123456", "2FA code field should work"

            # UI Verification: Login button should be available for final submission
            login_buttons = app.query("Button#login")

            await pilot.click(login_buttons.first())
            await pilot.pause()

            assert len(app.screen_stack) == 1, "Login modal should be closed"

            assert app.auth_status, "Authentication status should be True"


@pytest.mark.asyncio
async def test_logout_modal_interactions() -> None:
    """Test logout modal UI interactions."""

    with patch("dds_cli.dds_gui.pages.authentication.authentication_form.Auth") as mock_auth_class:
        mock_auth_instance = MagicMock()
        mock_auth_class.return_value = mock_auth_instance

        app = DDSApp(token_path="test_path")

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Push logout modal
            logout_modal = LogoutModal()

            with patch.object(logout_modal, "close_modal") as mock_close:
                app.push_screen(logout_modal)
                await pilot.pause()

                assert len(app.screen_stack) > 1, "Logout modal should be displayed"

                # Test cancel functionality
                cancel_button = app.query("Button#cancel")

                await pilot.click(cancel_button.first())
                await pilot.pause()
                assert mock_close.call_count >= 1, "Modal should close on cancel"
                app.pop_screen()  # Need to manually pop the screen
                assert app.auth_status, "Authentication status should be True still"

                app.push_screen(logout_modal)
                await pilot.pause()
                assert len(app.screen_stack) > 1, "Logout modal should be displayed"

                # Test logout functionality
                logout_button = app.query("Button#confirm")

                await pilot.click(logout_button.first())
                await pilot.pause()
                assert mock_close.call_count >= 1, "Modal should close on logout"
                app.pop_screen()
                assert not app.auth_status, "Authentication status should be False"


@pytest.mark.asyncio
async def test_reauthentication_modal_form_interactions() -> None:
    """Test reauthentication modal form interactions."""

    with patch("dds_cli.dds_gui.pages.authentication.authentication_form.Auth") as mock_auth_class:
        mock_auth_instance = MagicMock()
        mock_auth_class.return_value = mock_auth_instance
        mock_auth_instance.login.return_value = ("partial_token_456", "TOTP")
        mock_auth_instance.confirm_twofactor.return_value = None

        app = DDSApp(token_path="test_path")

        async with app.run_test() as pilot:
            app.set_auth_status(True)
            await pilot.pause()

            # Push reauthentication modal
            reauth_modal = ReAuthenticateModal()
            app.push_screen(reauth_modal)
            await pilot.pause()

            # Verify modal displayed
            assert len(app.screen_stack) > 1, "Reauthentication modal should be displayed"

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            assert username_inputs.first().value == "test_user"
            assert password_inputs.first().value == "test_password"

            # UI Workflow Test: Click "Send 2FA code" triggers form switch
            send_2fa_buttons = app.query("Button#send-2fa-code")

            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # UI Verification: 2FA form should now be displayed
            code_inputs = app.query("Input#code")

            # Test 2FA field interaction
            code_inputs.first().value = "123456"
            await pilot.pause()

            assert code_inputs.first().value == "123456", "2FA code field should work"

            # UI Verification: Login button should be available for final submission
            login_buttons = app.query("Button#login")

            await pilot.click(login_buttons.first())
            await pilot.pause()

            assert len(app.screen_stack) == 1, "Reauthentication modal should be closed"

            assert app.auth_status, "Authentication status should be True"


@pytest.mark.asyncio
async def test_keyboard_navigation() -> None:
    """Test keyboard navigation in authentication forms."""

    with patch("dds_cli.dds_gui.pages.authentication.authentication_form.Auth") as mock_auth_class:
        mock_auth_instance = MagicMock()
        mock_auth_class.return_value = mock_auth_instance

        app = DDSApp(token_path="test_path")

        async with app.run_test() as pilot:
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Test tab navigation between fields
            username_inputs = app.query("Input#username")
            if username_inputs:
                await pilot.click(username_inputs.first())
                await pilot.press("t", "e", "s", "t")
                await pilot.press("tab")  # Move to password field
                await pilot.press("p", "a", "s", "s")
                await pilot.pause()

                # Test escape to cancel
                await pilot.press("escape")
                await pilot.pause()
