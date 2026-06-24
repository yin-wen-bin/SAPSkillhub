from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "Common"
    / "sap-windowsgui-logon"
    / "scripts"
    / "logon.py"
)
SPEC = importlib.util.spec_from_file_location("sap_windowsgui_logon", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
logon = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(logon)


class SapWindowsGuiLogonTests(unittest.TestCase):
    def configuration(self) -> dict[str, str]:
        return {
            "Description": "Test DEV",
            "Client": "100",
            "User": "TEST_USER",
            "Password": "p@ ss&word",
            "LogonLanguage": "EN",
        }

    def test_read_configuration_normalizes_optional_system(self) -> None:
        content = self.configuration() | {"System": "s4h"}
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "config.json"
            path.write_text(json.dumps(content), encoding="utf-8")
            result = logon.read_configuration(path)

        self.assertEqual(result["System"], "S4H")
        self.assertEqual(result["Password"], content["Password"])

    def test_resolve_system_id_from_landscape_description(self) -> None:
        xml = (
            '<Landscape><Services><Service type="SAPGUI" name="Test DEV" '
            'systemid="S4H" /></Services></Landscape>'
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "SAPUILandscape.xml"
            path.write_text(xml, encoding="utf-8")
            result = logon.resolve_system_id(self.configuration(), [path])

        self.assertEqual(result, "S4H")

    def test_build_sapshcut_command_uses_argument_list_without_shell(self) -> None:
        command = logon.build_sapshcut_command(
            Path(r"C:\Program Files\SAP\FrontEnd\SAPGUI\sapshcut.exe"),
            "S4H",
            self.configuration(),
        )

        self.assertEqual(command[1], "-system=S4H")
        self.assertIn("-client=100", command)
        self.assertIn("-pw=p@ ss&word", command)
        self.assertEqual(len(command), 6)

    def test_compatible_mode_falls_back_only_for_primary_unavailable(self) -> None:
        with (
            mock.patch.object(
                logon,
                "log_on_with_scripting",
                side_effect=logon.PrimaryMethodUnavailable("disabled by server"),
            ),
            mock.patch.object(
                logon,
                "launch_sap_shortcut",
                return_value="S4H",
            ) as fallback,
        ):
            result = logon.log_on_compatible(
                self.configuration(), 60, None, None, True
            )

        self.assertEqual(result, ("sapshcut", "S4H", "disabled by server"))
        fallback.assert_called_once()

    def test_compatible_mode_does_not_fallback_after_login_error(self) -> None:
        with (
            mock.patch.object(
                logon,
                "log_on_with_scripting",
                side_effect=logon.LogonError("credentials rejected"),
            ),
            mock.patch.object(logon, "launch_sap_shortcut") as fallback,
        ):
            with self.assertRaisesRegex(logon.LogonError, "credentials rejected"):
                logon.log_on_compatible(
                    self.configuration(), 60, None, None, True
                )

        fallback.assert_not_called()

    def test_compatible_mode_honors_disabled_fallback(self) -> None:
        with (
            mock.patch.object(
                logon,
                "log_on_with_scripting",
                side_effect=logon.PrimaryMethodUnavailable("disabled by server"),
            ),
            mock.patch.object(logon, "launch_sap_shortcut") as fallback,
        ):
            with self.assertRaisesRegex(logon.LogonError, "fallback is disabled"):
                logon.log_on_compatible(
                    self.configuration(), 60, None, None, False
                )

        fallback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
