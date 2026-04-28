#!/usr/bin/env python3
"""
Cloud Phone Logger - Automatic logging for all cloud phone operations

Every cloud phone operation MUST generate a log file using this module.

Usage:
    # Method 1: Direct instantiation (for programmatic use)
    from scripts.cloudphone_logger import CloudPhoneLog

    log = CloudPhoneLog("task_name", phone_id)
    log.api_call("/open/v1/phone/start", {...})
    log.save()

    # Method 2: Context manager (auto-saves on exit)
    with CloudPhoneLog("task_name", phone_id) as log:
        log.api_call("/open/v1/phone/start", {...})
        log.step("UI", "click", "text='Submit'")
    # Log auto-saved to: logs/cloudphone/YYYYMMDD_HHMMSS_mmm_task_name_phoneid.log
"""

import json
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Any


# Sensitive field patterns for automatic log desensitization
_SENSITIVE_KEYS = {
    'token', 'pwd', 'password', 'passwd', 'secret', 'apikey', 'api_key',
    'authorization', 'proxy_password', 'proxy_pwd', 'access_key', 'secret_key',
    'credential', 'auth', 'email', 'account'
}


def _mask_sensitive_data(data: Any) -> Any:
    """
    Recursively mask sensitive fields in API request/response data.
    Prevents credentials, tokens, and PII from being written to log files.
    """
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            key_str = str(k).lower()
            if any(pattern in key_str for pattern in _SENSITIVE_KEYS):
                masked[k] = '***'
            else:
                masked[k] = _mask_sensitive_data(v)
        return masked
    elif isinstance(data, list):
        return [_mask_sensitive_data(item) for item in data]
    return data


class CloudPhoneLog:
    """Logger for cloud phone operations"""

    def __init__(self, task_name: str, phone_id: str, verbose: bool = True):
        self.task_name = task_name
        self.phone_id = phone_id
        self.verbose = verbose
        self.entries = []
        self.start_time = datetime.now()
        self.log_dir = self._get_log_dir()
        self.log_file = self._get_log_file()
        self._saved = False  # Prevent duplicate saves

    def __enter__(self):
        """Support context manager protocol"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Auto-save on context exit"""
        self.save()
        return False  # Don't suppress exceptions

    def _get_log_dir(self) -> Path:
        """Get log directory path using pathlib"""
        skill_dir = Path(__file__).resolve().parent
        log_dir = skill_dir.parent / 'logs' / 'cloudphone'
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    def _get_log_file(self) -> Path:
        """Get log file path with millisecond precision to avoid conflicts"""
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # YYYYMMDD_HHMMSS_mmm
        filename = f"{timestamp}_{self.task_name}_{self.phone_id}.log"
        return self.log_dir / filename

    def _add_entry(self, entry_type: str, **kwargs):
        """Add a log entry"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": entry_type,
            "task": self.task_name,
            "phone_id": self.phone_id,
            **kwargs
        }
        self.entries.append(entry)
        
        # Console output (optional)
        if self.verbose:
            # Filter out redundant fields for cleaner output
            details = {k: v for k, v in kwargs.items() if k not in ('task', 'phone_id')}
            print(f"  📝 LOG [{entry_type}]: {details}")

    def api_call(self, endpoint: str, data: dict, response_code: int = None, response_data: dict = None):
        """Log an API call with sensitive data automatically masked"""
        self._add_entry(
            "API_CALL",
            endpoint=endpoint,
            request_data=_mask_sensitive_data(data),
            response_code=response_code,
            response_data=_mask_sensitive_data(response_data)
        )

    def adb_cmd(self, command: str, rc: int = None, output: str = None):
        """Log an ADB command"""
        self._add_entry(
            "ADB_CMD",
            command=command,
            return_code=rc,
            output=output
        )

    def step(self, category: str, action: str, details: str = None):
        """Log a step"""
        self._add_entry(
            "STEP",
            category=category,
            action=action,
            details=details
        )

    def screenshot(self, path: str, size: int):
        """Log a screenshot"""
        self._add_entry(
            "SCREENSHOT",
            file_path=path,
            size_bytes=size
        )

    def file_op(self, action: str, path: str):
        """Log a file operation"""
        self._add_entry(
            "FILE_OP",
            action=action,
            file_path=path
        )

    def error(self, error_type: str, message: str, details: dict = None):
        """Log an error"""
        self._add_entry(
            "ERROR",
            error_type=error_type,
            message=message,
            details=details
        )

    def info(self, message: str):
        """Log an informational message"""
        self._add_entry(
            "INFO",
            message=message
        )

    def save(self) -> str:
        """Save log entries to file. Returns file path or empty string on failure."""
        if self._saved:
            return str(self.log_file)
        
        try:
            log_data = {
                "task": self.task_name,
                "phone_id": self.phone_id,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "entries": self.entries
            }

            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

            self._saved = True
            print(f"\n  📄 Log saved to: {self.log_file}")
            return str(self.log_file)
        except Exception as e:
            print(f"  ❌ Failed to save log: {e}")
            return ""


# Backward compatibility alias
@contextmanager
def CloudPhoneLogger(task_name: str, phone_id: str, verbose: bool = True):
    """
    Context manager for logging cloud phone operations.
    Deprecated: Use CloudPhoneLog directly with 'with' statement instead.
    """
    log = CloudPhoneLog(task_name, phone_id, verbose=verbose)
    try:
        yield log
    finally:
        log.save()


if __name__ == "__main__":
    # Test 1: Context manager usage
    print("Test 1: Context manager usage")
    with CloudPhoneLog("test_task", "test_phone_123") as log:
        log.api_call("/open/v1/phone/start", {"ids": ["test_phone_123"]}, response_code=0)
        log.adb_cmd("adb connect 1.2.3.4:5555", rc=0)
        log.step("UI", "click", "text='Submit'")
        log.screenshot("/tmp/test.png", 12345)
        log.info("Test completed")

    # Test 2: Duplicate save prevention
    print("\nTest 2: Duplicate save prevention")
    with CloudPhoneLog("test_task_2", "test_phone_456") as log:
        log.info("Testing duplicate save")
        log.save()  # First save
        log.save()  # Second save (should be ignored)

    # Test 3: Sensitive data masking
    print("\nTest 3: Log desensitization")
    sensitive_payload = {
        "token": "sk_live_abc123",
        "pwd": "my_secret_password",
        "ids": ["phone_001"],
        "proxy": {"password": "proxy_pass", "host": "1.2.3.4"},
        "nested": {"api_key": "key_xyz", "safe_field": "visible_data"},
        "list_data": [{"email": "user@example.com"}, {"normal": "value"}]
    }
    masked = _mask_sensitive_data(sensitive_payload)
    assert masked["token"] == "***", "Token should be masked"
    assert masked["pwd"] == "***", "Password should be masked"
    assert masked["proxy"]["password"] == "***", "Nested password should be masked"
    assert masked["nested"]["api_key"] == "***", "API key should be masked"
    assert masked["nested"]["safe_field"] == "visible_data", "Non-sensitive fields should remain"
    assert masked["list_data"][0]["email"] == "***", "Email in list should be masked"
    assert masked["list_data"][1]["normal"] == "value", "Normal list items should remain"
    print("✅ All sensitive fields correctly masked")

    print("\n✅ All tests passed!")
