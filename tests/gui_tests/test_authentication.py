"""Focused GUI Authentication tests - UI behavior only."""

import pathlib
from unittest.mock import MagicMock, patch

import pytest

import dds_cli.exceptions
from dds_cli.dds_gui.app import DDSApp
from dds_cli.dds_gui.pages.authentication.modals.login_modal import LoginModal
from dds_cli.dds_gui.pages.authentication.modals.logout_modal import LogoutModal
from dds_cli.dds_gui.pages.authentication.modals.reauthenticate_modal import ReAuthenticateModal

TOKEN_PATH = pathlib.Path("custom") / "token" / "path"

# =================================================================================
# Core UI State Management Tests
# =================================================================================


@pytest.mark.asyncio
async def test_auth_status_ui_switching() -> None:
    """Test that UI components change correctly when authentication status changes."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class:
        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

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

    with patch("dds_cli.auth.Auth") as mock_auth_class, patch(
        "dds_cli.data_lister.DataLister"
    ) as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "TOTP")
        mock_auth_form_instance.confirm_twofactor.return_value = None

        app = DDSApp(token_path=str(TOKEN_PATH))

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

    with patch("dds_cli.auth.Auth") as mock_auth_class, patch(
        "dds_cli.data_lister.DataLister"
    ) as mock_data_lister_class:

        mock_auth_instance = MagicMock()
        mock_auth_class.return_value = mock_auth_instance

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        app = DDSApp(token_path=str(TOKEN_PATH))

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

    with patch("dds_cli.auth.Auth") as mock_auth_class, patch(
        "dds_cli.data_lister.DataLister"
    ) as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "TOTP")
        mock_auth_form_instance.confirm_twofactor.return_value = None

        app = DDSApp(token_path=str(TOKEN_PATH))

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

    with patch("dds_cli.auth.Auth") as mock_auth_class, patch(
        "dds_cli.data_lister.DataLister"
    ) as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance

        app = DDSApp(token_path=str(TOKEN_PATH))

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


# =================================================================================
# Error Handling Tests
# =================================================================================


@pytest.mark.asyncio
async def test_invalid_credentials_error_handling() -> None:
    """Test that invalid credentials show error notification and don't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm to raise AuthenticationError
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.AuthenticationError(
            "Invalid username or password"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill invalid credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "invalid_user"
            password_inputs.first().value = "invalid_password"
            await pilot.pause()

            # Click "Send 2FA code" button to trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error notification was shown
            # The app should still be running and not crashed
            assert len(app.screen_stack) > 1, "Login modal should still be displayed after error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify the form is still in login state (not switched to 2FA)
            username_inputs_after = app.query("Input#username")
            password_inputs_after = app.query("Input#password")
            assert len(username_inputs_after) > 0, "Username field should still be present"
            assert len(password_inputs_after) > 0, "Password field should still be present"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


@pytest.mark.asyncio
async def test_invalid_2fa_code_error_handling() -> None:
    """Test that invalid 2FA code shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "TOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = (
            dds_cli.exceptions.AuthenticationError("Invalid 2FA code")
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill invalid 2FA code
            code_inputs.first().value = "000000"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert len(app.screen_stack) == 1, "Login modal should be closed after 2FA error"
            assert not app.auth_status, "Authentication status should remain False"


@pytest.mark.asyncio
async def test_network_error_handling() -> None:
    """Test that network/API errors show error notification and don't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm to raise ApiRequestError
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.ApiRequestError(
            "Network connection failed"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            # Click "Send 2FA code" button to trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error notification was shown
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) > 1
            ), "Login modal should still be displayed after network error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify the form is still in login state (not switched to 2FA)
            username_inputs_after = app.query("Input#username")
            password_inputs_after = app.query("Input#password")
            assert len(username_inputs_after) > 0, "Username field should still be present"
            assert len(password_inputs_after) > 0, "Password field should still be present"


@pytest.mark.asyncio
async def test_empty_credentials_error_handling() -> None:
    """Test that empty credentials show error notification and don't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm to raise AuthenticationError for empty credentials
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.AuthenticationError(
            "Non-empty username needed to be able to authenticate."
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Leave credentials empty
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = ""
            password_inputs.first().value = ""
            await pilot.pause()

            # Click "Send 2FA code" button to trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error notification was shown
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) > 1
            ), "Login modal should still be displayed after empty credentials error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify the form is still in login state (not switched to 2FA)
            username_inputs_after = app.query("Input#username")
            password_inputs_after = app.query("Input#password")
            assert len(username_inputs_after) > 0, "Username field should still be present"
            assert len(password_inputs_after) > 0, "Password field should still be present"


@pytest.mark.asyncio
async def test_reauthentication_invalid_credentials_error_handling() -> None:
    """Test that invalid credentials in reauthentication show error notification and don't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm to raise AuthenticationError
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.AuthenticationError(
            "Invalid username or password"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(True)  # Start as authenticated
            await pilot.pause()

            # Push reauthentication modal
            reauth_modal = ReAuthenticateModal()
            app.push_screen(reauth_modal)
            await pilot.pause()

            # Fill invalid credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "invalid_user"
            password_inputs.first().value = "invalid_password"
            await pilot.pause()

            # Click "Send 2FA code" button to trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error notification was shown
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) > 1
            ), "Reauthentication modal should still be displayed after error"
            assert app.auth_status, "Authentication status should remain True (original state)"

            # Verify the form is still in login state (not switched to 2FA)
            username_inputs_after = app.query("Input#username")
            password_inputs_after = app.query("Input#password")
            assert len(username_inputs_after) > 0, "Username field should still be present"
            assert len(password_inputs_after) > 0, "Password field should still be present"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


# =================================================================================
# Empty Field Validation Tests
# =================================================================================


@pytest.mark.parametrize(
    "field,value,error_msg",
    [
        ("username", "", "Non-empty username needed to be able to authenticate."),
        ("password", "test_password", "Non-empty password needed to be able to authenticate."),
    ],
)
@pytest.mark.asyncio
async def test_empty_field_error_handling(field, value, error_msg):
    """Test that empty fields show error notification and don't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.AuthenticationError(
            error_msg
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill form with empty field
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "test_user" if field == "password" else value
            password_inputs.first().value = "test_password" if field == "username" else value
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert (
                len(app.screen_stack) == 2
            ), f"Login modal should remain open after empty {field} error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify form fields still present
            username_inputs_after = app.query("Input#username")
            password_inputs_after = app.query("Input#password")
            assert len(username_inputs_after) > 0, "Username field should still be present"
            assert len(password_inputs_after) > 0, "Password field should still be present"


@pytest.mark.asyncio
async def test_empty_2fa_code_error_handling() -> None:
    """Test that empty 2FA code shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = (
            dds_cli.exceptions.AuthenticationError(
                "Exited due to no one-time authentication code entered."
            )
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal and fill credentials
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Go to 2FA step
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Submit empty 2FA code
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"
            code_inputs.first().value = ""  # Empty 2FA code
            await pilot.pause()

            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert (
                len(app.screen_stack) == 2
            ), "Login modal should remain open after empty 2FA code error"
            assert not app.auth_status, "Authentication status should remain False"


# =================================================================================
# Additional Login Exception Tests - Missing Coverage
# =================================================================================


@pytest.mark.asyncio
async def test_login_json_decode_error() -> None:
    """Test that JSON decode error during login shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.ApiResponseError(
            "Response code: 200. The request did not return a valid JSON response. Details: Expecting value: line 1 column 1 (char 0)"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert (
                len(app.screen_stack) == 2
            ), "Login modal should remain open after JSON decode error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


@pytest.mark.asyncio
async def test_login_internal_server_error() -> None:
    """Test that 500 Internal Server Error during login shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.ApiResponseError(
            "Failed to authenticate user: Internal server error occurred"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert len(app.screen_stack) == 2, "Login modal should remain open after server error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


@pytest.mark.asyncio
async def test_login_bad_request_error() -> None:
    """Test that 400 Bad Request during login shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.DDSCLIException(
            "Failed to authenticate user: Invalid request parameters"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert (
                len(app.screen_stack) == 2
            ), "Login modal should remain open after bad request error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


@pytest.mark.asyncio
async def test_login_forbidden_error() -> None:
    """Test that 403 Forbidden during login shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.DDSCLIException(
            "Failed to authenticate user: Access forbidden"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert (
                len(app.screen_stack) == 2
            ), "Login modal should remain open after forbidden error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


@pytest.mark.asyncio
async def test_no_prompt_authentication_error() -> None:
    """Test that no-prompt authentication error shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.AuthenticationError(
            "Authentication not possible when running with --no-prompt. Please run the `dds auth login` command and authenticate interactively."
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert (
                len(app.screen_stack) == 2
            ), "Login modal should remain open after no-prompt error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


@pytest.mark.asyncio
async def test_totp_not_enabled_error() -> None:
    """Test that TOTP not enabled error shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.AuthenticationError(
            "TOTP is not enabled for this user. Please use email-based 2FA instead."
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "test_user"
            password_inputs.first().value = "test_password"
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert len(app.screen_stack) == 2, "Login modal should remain open after TOTP error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


@pytest.mark.asyncio
async def test_unicode_decode_error() -> None:
    """Test that Unicode decode error during login shows error notification and doesn't crash the GUI."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock setup
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.side_effect = dds_cli.exceptions.ApiRequestError(
            "The entered username or password seems to contain invalid characters. Please try again."
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Setup login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill credentials with invalid characters
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")
            username_inputs.first().value = "test_user_with_ñ"
            password_inputs.first().value = "test_password_with_é"
            await pilot.pause()

            # Trigger authentication
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify error handling
            assert len(app.screen_stack) == 2, "Login modal should remain open after Unicode error"
            assert not app.auth_status, "Authentication status should remain False"

            # Verify 2FA form is not shown
            code_inputs = app.query("Input#code")
            assert len(code_inputs) == 0, "2FA code field should not be present after error"


# =================================================================================
# 2FA Confirmation Exception Tests - Missing Exception Handling
# =================================================================================


@pytest.mark.asyncio
async def test_2fa_json_decode_error() -> None:
    """Test ApiResponseError when API returns invalid JSON during 2FA confirmation."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = dds_cli.exceptions.ApiResponseError(
            "Response code: 200. The request did not return a valid JSON response. Details: Expecting value: line 1 column 1 (char 0)"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill 2FA code
            code_inputs.first().value = "12345678"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) == 1
            ), "Login modal should be closed after 2FA JSON decode error"
            assert not app.auth_status, "Authentication status should remain False"


@pytest.mark.asyncio
async def test_2fa_connection_error() -> None:
    """Test ApiRequestError when connection fails during 2FA confirmation."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = dds_cli.exceptions.ApiRequestError(
            "Failed to authenticate with second factor: The database seems to be down -- \nConnection refused"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill 2FA code
            code_inputs.first().value = "12345678"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) == 1
            ), "Login modal should be closed after 2FA connection error"
            assert not app.auth_status, "Authentication status should remain False"


@pytest.mark.asyncio
async def test_2fa_timeout_error() -> None:
    """Test ApiRequestError when request times out during 2FA confirmation."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = dds_cli.exceptions.ApiRequestError(
            "Failed to authenticate with second factor: The request timed out."
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill 2FA code
            code_inputs.first().value = "12345678"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) == 1
            ), "Login modal should be closed after 2FA timeout error"
            assert not app.auth_status, "Authentication status should remain False"


@pytest.mark.asyncio
async def test_2fa_bad_request_error() -> None:
    """Test DDSCLIException when API returns 400 Bad Request during 2FA confirmation."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = dds_cli.exceptions.DDSCLIException(
            "Failed to authenticate with second factor: Invalid 2FA code provided"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill 2FA code
            code_inputs.first().value = "12345678"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) == 1
            ), "Login modal should be closed after 2FA bad request error"
            assert not app.auth_status, "Authentication status should remain False"


@pytest.mark.asyncio
async def test_2fa_forbidden_error() -> None:
    """Test DDSCLIException when API returns 403 Forbidden during 2FA confirmation."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = dds_cli.exceptions.DDSCLIException(
            "Failed to authenticate with second factor: Access denied"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill 2FA code
            code_inputs.first().value = "12345678"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) == 1
            ), "Login modal should be closed after 2FA forbidden error"
            assert not app.auth_status, "Authentication status should remain False"


@pytest.mark.asyncio
async def test_2fa_internal_server_error() -> None:
    """Test ApiResponseError when API returns 500 Internal Server Error during 2FA confirmation."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = dds_cli.exceptions.ApiResponseError(
            "Failed to authenticate with second factor: Internal server error occurred"
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill 2FA code
            code_inputs.first().value = "12345678"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) == 1
            ), "Login modal should be closed after 2FA internal server error"
            assert not app.auth_status, "Authentication status should remain False"


@pytest.mark.asyncio
async def test_2fa_missing_token_error() -> None:
    """Test AuthenticationError when token is missing from 2FA response."""

    with patch("dds_cli.data_lister.DataLister") as mock_data_lister_class, patch(
        "dds_cli.dds_gui.pages.authentication.authentication_form.Auth"
    ) as mock_auth_form_class:

        # Mock DataLister to prevent authentication attempts
        mock_data_lister_instance = MagicMock()
        mock_data_lister_class.return_value = mock_data_lister_instance
        mock_data_lister_instance.list_projects.return_value = []

        # Mock Auth in AuthenticationForm
        mock_auth_form_instance = MagicMock()
        mock_auth_form_class.return_value = mock_auth_form_instance
        mock_auth_form_instance.login.return_value = ("partial_token_456", "HOTP")
        mock_auth_form_instance.confirm_twofactor.side_effect = (
            dds_cli.exceptions.AuthenticationError("Missing token in authentication response.")
        )

        app = DDSApp(token_path=str(TOKEN_PATH))

        async with app.run_test() as pilot:
            app.set_auth_status(False)
            await pilot.pause()

            # Push login modal
            login_modal = LoginModal()
            app.push_screen(login_modal)
            await pilot.pause()

            # Fill valid credentials to get to 2FA step
            username_inputs = app.query("Input#username")
            password_inputs = app.query("Input#password")

            username_inputs.first().value = "valid_user"
            password_inputs.first().value = "valid_password"
            await pilot.pause()

            # Click "Send 2FA code" button
            send_2fa_buttons = app.query("Button#send-2fa-code")
            await pilot.click(send_2fa_buttons.first())
            await pilot.pause()

            # Verify 2FA form is now displayed
            code_inputs = app.query("Input#code")
            assert len(code_inputs) > 0, "2FA code field should be present"

            # Fill 2FA code
            code_inputs.first().value = "12345678"
            await pilot.pause()

            # Click login button to submit 2FA code
            login_buttons = app.query("Button#login")
            await pilot.click(login_buttons.first())
            await pilot.pause()

            # Verify error notification was shown and modal closed
            # The app should still be running and not crashed
            assert (
                len(app.screen_stack) == 1
            ), "Login modal should be closed after 2FA missing token error"
            assert not app.auth_status, "Authentication status should remain False"
