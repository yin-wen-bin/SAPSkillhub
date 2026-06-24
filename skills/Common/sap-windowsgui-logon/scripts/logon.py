from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

try:
    import pythoncom
    import win32com.client
    import winreg
except ImportError as exc:  # pragma: no cover - environment dependent
    WINDOWS_IMPORT_ERROR: Exception | None = exc
else:
    WINDOWS_IMPORT_ERROR = None


DEFAULT_CONFIG = Path.home() / ".sap-windowsgui-logon" / "config.json"
SECURITY_KEY = r"Software\SAP\SAPGUI Front\SAP Frontend Server\Security"
REQUIRED_FIELDS = ("Description", "Client", "User", "Password", "LogonLanguage")


class LogonError(RuntimeError):
    """A sanitized SAP logon failure safe to show to the user."""


class PrimaryMethodUnavailable(LogonError):
    """The scripting method failed before credentials were submitted."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Log on to SAP GUI for Windows")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--sap-logon-path", type=Path)
    parser.add_argument("--sap-shcut-path", type=Path)
    parser.add_argument("--disable-sapshcut-fallback", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    return parser


def read_configuration(path: Path) -> dict[str, str]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise LogonError(f"Configuration file not found: {resolved}")

    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LogonError(
            "The configuration file could not be read as valid UTF-8 JSON."
        ) from exc

    if not isinstance(raw, dict):
        raise LogonError("The configuration root must be a JSON object.")

    configuration: dict[str, str] = {}
    for name in REQUIRED_FIELDS:
        value = raw.get(name)
        if not isinstance(value, str):
            raise LogonError(
                f"Configuration field '{name}' is required and must be a JSON string."
            )
        if not value.strip():
            raise LogonError(f"Configuration field '{name}' must not be empty.")
        configuration[name] = value if name == "Password" else value.strip()

    if not re.fullmatch(r"\d{3}", configuration["Client"]):
        raise LogonError(
            "Configuration field 'Client' must be a three-digit string such as '100'."
        )

    configuration["LogonLanguage"] = configuration["LogonLanguage"].upper()
    if not re.fullmatch(r"[A-Z]{2}", configuration["LogonLanguage"]):
        raise LogonError(
            "Configuration field 'LogonLanguage' must contain two letters such as 'EN'."
        )

    system = raw.get("System")
    if system is not None:
        if not isinstance(system, str) or not re.fullmatch(
            r"[A-Za-z0-9]{3}", system.strip()
        ):
            raise LogonError(
                "Optional configuration field 'System' must be a three-character SAP "
                "system ID such as 'S4H'."
            )
        configuration["System"] = system.strip().upper()
    return configuration


def require_windows_runtime() -> None:
    if os.name != "nt":
        raise LogonError("SAP GUI for Windows logon requires Windows.")
    if sys.version_info < (3, 11):
        raise LogonError("Python 3.11 or later is required.")
    if WINDOWS_IMPORT_ERROR is not None:
        raise LogonError(
            "The pywin32 dependency is unavailable. Install scripts/requirements.txt."
        )


def read_registry_dword(name: str) -> int | None:
    assert WINDOWS_IMPORT_ERROR is None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SECURITY_KEY) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return int(value)
    except (FileNotFoundError, OSError, TypeError, ValueError):
        return None


def assert_scripting_warnings_disabled() -> None:
    enabled = [
        name
        for name in ("WarnOnConnection", "WarnOnAttach")
        if read_registry_dword(name) == 1
    ]
    if enabled:
        raise PrimaryMethodUnavailable(
            "SAP GUI requires manual scripting confirmation "
            f"({', '.join(enabled)}). Disable these warnings in SAP GUI options; "
            "the scripting method stopped before submitting credentials."
        )


def registry_executable_candidates(executable_name: str) -> list[Path]:
    assert WINDOWS_IMPORT_ERROR is None
    candidates: list[Path] = []
    registry_path = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths" + "\\" + executable_name
    )
    for access in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                registry_path,
                access=winreg.KEY_READ | access,
            ) as key:
                value, _ = winreg.QueryValueEx(key, "")
                if value:
                    candidates.append(Path(str(value)))
        except (FileNotFoundError, OSError):
            continue
    return candidates


def find_sap_logon_executable(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        resolved = explicit_path.expanduser().resolve()
        if not resolved.is_file():
            raise LogonError(
                f"SAP Logon executable not found at the supplied path: {resolved}"
            )
        return resolved

    candidates = registry_executable_candidates("saplogon.exe")
    for environment_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(environment_name)
        if root:
            candidates.append(Path(root) / "SAP" / "FrontEnd" / "SAPGUI" / "saplogon.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise LogonError(
        "SAP Logon (saplogon.exe) was not found. Supply its full path with "
        "--sap-logon-path."
    )


def find_sap_shortcut_executable(
    explicit_path: Path | None,
    sap_logon_path: Path | None,
) -> Path:
    if explicit_path is not None:
        resolved = explicit_path.expanduser().resolve()
        if not resolved.is_file():
            raise LogonError(
                f"SAP Shortcut executable not found at the supplied path: {resolved}"
            )
        return resolved

    candidates: list[Path] = []
    if sap_logon_path is not None:
        candidates.append(sap_logon_path.expanduser().resolve().parent / "sapshcut.exe")
    candidates.extend(registry_executable_candidates("sapshcut.exe"))
    for environment_name in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(environment_name)
        if root:
            candidates.append(Path(root) / "SAP" / "FrontEnd" / "SAPGUI" / "sapshcut.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise LogonError(
        "SAP Shortcut (sapshcut.exe) was not found. Supply its full path with "
        "--sap-shcut-path."
    )


def default_landscape_paths() -> list[Path]:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return []
    common = Path(appdata) / "SAP" / "Common"
    return [
        common / "SAPUILandscape.xml",
        common / "SAPUILandscapeGlobal.xml",
    ]


def system_ids_from_landscapes(
    description: str,
    paths: Iterable[Path],
) -> set[str]:
    matches: set[str] = set()
    for path in paths:
        if not path.is_file():
            continue
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            continue
        for element in root.iter():
            attributes = {key.lower(): value for key, value in element.attrib.items()}
            if attributes.get("name") != description:
                continue
            system_id = attributes.get("systemid", "").strip().upper()
            if system_id:
                matches.add(system_id)
    return matches


def resolve_system_id(
    configuration: dict[str, str],
    landscape_paths: Iterable[Path] | None = None,
) -> str:
    configured = configuration.get("System")
    if configured:
        return configured

    paths = list(landscape_paths) if landscape_paths is not None else default_landscape_paths()
    matches = system_ids_from_landscapes(configuration["Description"], paths)
    if len(matches) == 1:
        return next(iter(matches))
    if not matches:
        raise LogonError(
            "SAP Shortcut fallback could not map Description to a system ID in "
            "SAPUILandscape.xml. Add optional field 'System' to the configuration."
        )
    raise LogonError(
        "SAP Shortcut fallback found multiple system IDs for the configured Description. "
        "Add optional field 'System' to the configuration."
    )


def build_sapshcut_command(
    executable: Path,
    system_id: str,
    configuration: dict[str, str],
) -> list[str]:
    return [
        str(executable),
        f"-system={system_id}",
        f"-client={configuration['Client']}",
        f"-user={configuration['User']}",
        f"-pw={configuration['Password']}",
        f"-language={configuration['LogonLanguage']}",
    ]


def launch_sap_shortcut(
    configuration: dict[str, str],
    timeout: int,
    explicit_shortcut_path: Path | None,
    explicit_logon_path: Path | None,
) -> str:
    system_id = resolve_system_id(configuration)
    executable = find_sap_shortcut_executable(
        explicit_shortcut_path,
        explicit_logon_path,
    )
    command = build_sapshcut_command(executable, system_id, configuration)
    try:
        completed = subprocess.run(
            command,
            check=False,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=min(timeout, 30),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise LogonError(
            "SAP Shortcut did not return within 30 seconds and was stopped to limit "
            "password exposure in the process command line."
        ) from exc
    except OSError as exc:
        raise LogonError("SAP Shortcut could not be started.") from exc
    finally:
        if "completed" in locals():
            completed.args = []
        for index in range(len(command)):
            command[index] = ""

    if completed.returncode != 0:
        raise LogonError(
            f"SAP Shortcut exited with code {completed.returncode}; logon was not confirmed."
        )
    return system_id


def get_scripting_engine() -> Any | None:
    assert WINDOWS_IMPORT_ERROR is None
    try:
        sap_gui = win32com.client.GetObject("SAPGUI")
        application = sap_gui.GetScriptingEngine
        return application if application is not None else None
    except Exception:
        return None


def wait_for_scripting_engine(
    deadline: float,
    explicit_executable: Path | None,
) -> Any:
    application = get_scripting_engine()
    if application is None:
        executable = find_sap_logon_executable(explicit_executable)
        subprocess.Popen([str(executable)], close_fds=True)

    while time.monotonic() < deadline:
        application = get_scripting_engine()
        if application is not None:
            return application
        time.sleep(0.5)
    raise PrimaryMethodUnavailable(
        "SAP GUI Scripting was not available before the timeout. Verify that SAP "
        "Logon is running and scripting is enabled."
    )


def first_child(parent: Any) -> Any | None:
    try:
        if int(parent.Children.Count) > 0:
            return parent.Children(0)
    except Exception:
        return None
    return None


def wait_for_session(connection: Any, deadline: float) -> Any:
    while time.monotonic() < deadline:
        session = first_child(connection)
        if session is not None:
            return session
        time.sleep(0.25)
    raise PrimaryMethodUnavailable(
        "SAP opened the connection but did not create a session before the timeout."
    )


def find_control(session: Any, control_id: str) -> Any | None:
    try:
        return session.FindById(control_id, False)
    except Exception:
        try:
            return session.FindById(control_id)
        except Exception:
            return None


def wait_for_control(session: Any, control_id: str, deadline: float) -> Any:
    while time.monotonic() < deadline:
        control = find_control(session, control_id)
        if control is not None:
            return control
        time.sleep(0.25)
    raise PrimaryMethodUnavailable(
        f"SAP login control '{control_id}' was not available before the timeout."
    )


def wait_for_authentication(
    session: Any,
    configuration: dict[str, str],
    deadline: float,
) -> None:
    while time.monotonic() < deadline:
        if find_control(session, "wnd[1]") is not None:
            raise LogonError(
                "SAP displayed a secondary dialog after credential submission. Resolve "
                "it manually; no option was selected automatically."
            )

        try:
            session_client = str(session.Info.Client)
            session_user = str(session.Info.User)
            if session_client == configuration["Client"] and session_user.strip():
                return
        except Exception:
            pass

        status_bar = find_control(session, "wnd[0]/sbar")
        if status_bar is not None:
            try:
                message_type = str(status_bar.MessageType)
                message = str(status_bar.Text).strip()
            except Exception:
                message_type = ""
                message = ""
            if message_type in {"E", "A"}:
                raise LogonError(
                    f"SAP logon failed: {message or 'SAP rejected the logon request.'}"
                )
        time.sleep(0.25)
    raise LogonError("SAP did not confirm authentication before the timeout.")


def close_connection(connection: Any | None) -> None:
    if connection is None:
        return
    try:
        connection.CloseConnection()
    except Exception:
        pass


def log_on_with_scripting(
    configuration: dict[str, str],
    timeout: int,
    explicit_executable: Path | None,
) -> None:
    require_windows_runtime()
    assert_scripting_warnings_disabled()
    deadline = time.monotonic() + timeout
    assert WINDOWS_IMPORT_ERROR is None
    pythoncom.CoInitialize()
    connection = None
    try:
        application = wait_for_scripting_engine(deadline, explicit_executable)
        try:
            connection = application.OpenConnection(
                configuration["Description"], True
            )
        except Exception as exc:
            raise LogonError(
                "SAP could not open the configured Description. Verify that it exactly "
                "matches an SAP Logon entry."
            ) from exc
        if connection is None:
            raise LogonError(
                "SAP did not return a connection for the configured Description."
            )
        try:
            disabled_by_server = bool(connection.DisabledByServer)
        except Exception:
            disabled_by_server = False
        if disabled_by_server:
            raise PrimaryMethodUnavailable(
                "SAP GUI Scripting is disabled by the target SAP server."
            )

        session = wait_for_session(connection, deadline)
        controls = {
            "Client": wait_for_control(
                session, "wnd[0]/usr/txtRSYST-MANDT", deadline
            ),
            "User": wait_for_control(
                session, "wnd[0]/usr/txtRSYST-BNAME", deadline
            ),
            "Password": wait_for_control(
                session, "wnd[0]/usr/pwdRSYST-BCODE", deadline
            ),
            "LogonLanguage": wait_for_control(
                session, "wnd[0]/usr/txtRSYST-LANGU", deadline
            ),
        }
        main_window = wait_for_control(session, "wnd[0]", deadline)
        for field, control in controls.items():
            control.Text = configuration[field]
        main_window.SendVKey(0)
        wait_for_authentication(session, configuration, deadline)
    except PrimaryMethodUnavailable:
        close_connection(connection)
        raise
    finally:
        pythoncom.CoUninitialize()


def log_on_compatible(
    configuration: dict[str, str],
    timeout: int,
    explicit_logon_path: Path | None,
    explicit_shortcut_path: Path | None,
    fallback_enabled: bool,
) -> tuple[str, str | None, str | None]:
    try:
        log_on_with_scripting(configuration, timeout, explicit_logon_path)
        return "scripting", None, None
    except PrimaryMethodUnavailable as primary_error:
        if not fallback_enabled:
            raise LogonError(
                f"Primary SAP GUI Scripting method is unavailable: {primary_error} "
                "SAP Shortcut fallback is disabled."
            ) from primary_error
        system_id = launch_sap_shortcut(
            configuration,
            timeout,
            explicit_shortcut_path,
            explicit_logon_path,
        )
        return "sapshcut", system_id, str(primary_error)


def main() -> int:
    args = build_parser().parse_args()
    if not 5 <= args.timeout <= 600:
        print("Timeout must be between 5 and 600 seconds.", file=sys.stderr)
        return 1

    configuration: dict[str, str] | None = None
    try:
        configuration = read_configuration(args.config)
        if args.validate_only:
            fallback_status = ""
            if not args.disable_sapshcut_fallback:
                require_windows_runtime()
                system_id = resolve_system_id(configuration)
                find_sap_shortcut_executable(
                    args.sap_shcut_path,
                    args.sap_logon_path,
                )
                fallback_status = (
                    f" SAP Shortcut fallback is available for System '{system_id}'."
                )
            print(
                "Configuration is valid for Description "
                f"'{configuration['Description']}', Client '{configuration['Client']}', "
                f"and LogonLanguage '{configuration['LogonLanguage']}'."
                f"{fallback_status}"
            )
            return 0
        method, system_id, primary_reason = log_on_compatible(
            configuration,
            args.timeout,
            args.sap_logon_path,
            args.sap_shcut_path,
            not args.disable_sapshcut_fallback,
        )
        if method == "scripting":
            print(
                "SAP GUI logon succeeded through SAP GUI Scripting for Description "
                f"'{configuration['Description']}' and Client '{configuration['Client']}'."
            )
        else:
            print(
                "Primary SAP GUI Scripting method was unavailable: "
                f"{primary_reason} SAP Shortcut fallback started for System "
                f"'{system_id}' and Client '{configuration['Client']}'. Authentication "
                "cannot be verified because SAP GUI Scripting is unavailable."
            )
        return 0
    except LogonError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("SAP GUI logon failed because of an unexpected local automation error.", file=sys.stderr)
        return 1
    finally:
        if configuration is not None:
            configuration["Password"] = ""


if __name__ == "__main__":
    raise SystemExit(main())
