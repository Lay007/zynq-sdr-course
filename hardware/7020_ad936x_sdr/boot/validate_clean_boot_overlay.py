#!/usr/bin/env python3
"""Validate the clean boot overlay against a chosen PL image.

The script automates the exact bring-up loop used during live debugging:

1. mount the FAT boot partition over SSH;
2. upload a candidate PL image plus the matching `uEnv.txt` when needed;
3. reboot the board and capture UART output;
4. verify that Linux comes up with AD9361 and IIO devices alive.
"""

from __future__ import annotations

import argparse
import hashlib
import shlex
import socket
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from extract_stock_system_top_partition import find_partition


BOOT_DIR = Path(__file__).resolve().parent
BUNDLE_ROOT = BOOT_DIR.parent
DEFAULT_BOOT_BIN = BOOT_DIR / "sd_image" / "BOOT.bin"
DEFAULT_REFERENCE_SYSTEM_BIT = (
    BUNDLE_ROOT / "ps" / "ad936x_no_os_reference" / "platform" / "hw" / "system_top.bit"
)
DEFAULT_STOCK_SYSTEM_BIT_BIN = BUNDLE_ROOT / "stock_system_top_from_BOOT.bin"
DEFAULT_UENV = BOOT_DIR / "course_clean" / "uEnv_course_bpsk_overlay.txt"
DEFAULT_UART_LOG = BOOT_DIR / "last_clean_boot_overlay_uart.log"
DEFAULT_HOST = "192.168.40.1"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = "analog"
DEFAULT_PORT = 22
DEFAULT_SERIAL_PORT = "COM6"
DEFAULT_BAUDRATE = 115200
REMOTE_MOUNT = "/mnt/msd"


@dataclass(frozen=True)
class ValidationSummary:
    local_path: str
    remote_path: str
    local_md5: str
    remote_md5: str
    uenv_path: str
    uenv_md5: str
    uart_log_path: str
    ad9361_initialized: bool
    iio_device_count: int
    iio_devices: list[str]
    dmesg_ad9361: str


class ParamikoSession:
    def __init__(
        self,
        *,
        host: str,
        user: str,
        password: str,
        port: int,
        timeout_s: float,
    ) -> None:
        try:
            import paramiko
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "This script requires paramiko. Install dependencies from requirements.txt."
            ) from exc

        self._paramiko = paramiko
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(
            hostname=host,
            username=user,
            password=password,
            port=port,
            timeout=timeout_s,
            banner_timeout=timeout_s,
            auth_timeout=timeout_s,
            look_for_keys=False,
            allow_agent=False,
        )

    def run(self, command: str, *, timeout_s: float = 30.0) -> tuple[int, str, str]:
        sentinel = "__CODEX_RC__:"
        wrapped = shlex.quote(f"{command}; rc=$?; printf '{sentinel}%d\\n' \"$rc\"")
        stdin, stdout, stderr = self.client.exec_command(
            command=f"sh -lc {wrapped}",
            timeout=timeout_s,
        )
        del stdin
        stdout_text = stdout.read().decode("utf-8", errors="replace")
        stderr_text = stderr.read().decode("utf-8", errors="replace")
        returncode = stdout.channel.recv_exit_status()
        lines = stdout_text.splitlines()
        for index in range(len(lines) - 1, -1, -1):
            if lines[index].startswith(sentinel):
                returncode = int(lines[index].split(":", 1)[1])
                lines.pop(index)
                stdout_text = "\n".join(lines)
                if stdout_text:
                    stdout_text += "\n"
                break
        return returncode, stdout_text, stderr_text

    def upload_via_cat(self, remote_path: str, payload: bytes) -> None:
        stdin, stdout, stderr = self.client.exec_command(
            f"sh -c 'cat > {remote_path}'",
            timeout=300,
        )
        chunk_size = 32768
        sent = 0
        view = memoryview(payload)
        while sent < len(payload):
            chunk = view[sent : sent + chunk_size]
            stdin.write(chunk)
            stdin.flush()
            sent += len(chunk)
        stdin.close()
        stdout_text = stdout.read().decode("utf-8", errors="replace")
        stderr_text = stderr.read().decode("utf-8", errors="replace")
        returncode = stdout.channel.recv_exit_status()
        if returncode != 0:
            raise RuntimeError(
                f"Upload failed with rc={returncode}: {stderr_text.strip() or stdout_text.strip() or 'no diagnostic output'}"
            )

    def reboot(self) -> None:
        try:
            self.client.exec_command("reboot", timeout=5)
        except Exception:
            pass

    def close(self) -> None:
        self.client.close()


def md5_bytes(payload: bytes) -> str:
    return hashlib.md5(payload).hexdigest()


def ensure_stock_baseline(path: Path, boot_bin_path: Path) -> None:
    if path.exists():
        return
    boot_blob = boot_bin_path.read_bytes()
    partition_offset, partition_length = find_partition(boot_blob, "system_top.bit")
    path.write_bytes(boot_blob[partition_offset : partition_offset + partition_length])


def wait_for_port_state(host: str, port: int, *, want_open: bool, timeout_s: float) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        try:
            sock.connect((host, port))
            sock.close()
            if want_open:
                return True
        except OSError:
            if not want_open:
                return True
        time.sleep(1.0)
    return False


def capture_uart_log(
    *,
    serial_port: str,
    baudrate: int,
    log_path: Path,
    capture_timeout_s: float,
) -> None:
    try:
        import serial
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "This script requires pyserial. Install dependencies from requirements.txt."
        ) from exc

    ser = serial.Serial(serial_port, baudrate, timeout=0.2)
    try:
        ser.reset_input_buffer()
        deadline = time.time() + capture_timeout_s
        chunks: list[str] = []
        seen_login = False
        login_seen_at = 0.0
        while time.time() < deadline:
            data = ser.read(4096)
            if data:
                text = data.decode("utf-8", errors="replace")
                chunks.append(text)
                if "pluto login:" in text or "login:" in text:
                    if not seen_login:
                        seen_login = True
                        login_seen_at = time.time()
                if seen_login and time.time() - login_seen_at > 3.0:
                    break
            elif seen_login and time.time() - login_seen_at > 3.0:
                break
        log_path.write_text("".join(chunks), encoding="utf-8", errors="replace")
    finally:
        ser.close()


def run_remote_checked(session: ParamikoSession, command: str, *, context: str) -> str:
    returncode, stdout_text, stderr_text = session.run(command)
    if returncode != 0:
        raise RuntimeError(
            f"{context} failed with rc={returncode}: "
            f"{stderr_text.strip() or stdout_text.strip() or 'no diagnostic output'}"
        )
    return stdout_text.strip()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--system-bit-bin",
        type=Path,
        default=DEFAULT_REFERENCE_SYSTEM_BIT,
        help="Input candidate path: raw .bit for the clean-boot overlay, or a prebuilt .bit.bin for fallback experiments.",
    )
    parser.add_argument("--boot-bin", type=Path, default=DEFAULT_BOOT_BIN)
    parser.add_argument("--uenv", type=Path, help="Optional uEnv.txt override to copy to the FAT root before reboot.")
    parser.add_argument("--boot-mount", default=REMOTE_MOUNT)
    parser.add_argument("--ssh-host", default=DEFAULT_HOST)
    parser.add_argument("--ssh-user", default=DEFAULT_USER)
    parser.add_argument("--ssh-password", default=DEFAULT_PASSWORD)
    parser.add_argument("--ssh-port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ssh-timeout-s", type=float, default=10.0)
    parser.add_argument("--serial-port", default=DEFAULT_SERIAL_PORT)
    parser.add_argument("--baudrate", type=int, default=DEFAULT_BAUDRATE)
    parser.add_argument("--uart-log", type=Path, default=DEFAULT_UART_LOG)
    parser.add_argument("--reboot-timeout-s", type=float, default=120.0)
    parser.add_argument("--uart-capture-timeout-s", type=float, default=240.0)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    candidate_path = args.system_bit_bin
    if candidate_path == DEFAULT_STOCK_SYSTEM_BIT_BIN:
        ensure_stock_baseline(candidate_path, args.boot_bin)
    if not candidate_path.exists():
        raise FileNotFoundError(f"Missing system bitstream candidate: {candidate_path}")

    candidate_suffix = candidate_path.suffix.lower()
    remote_name = "system.bit" if candidate_suffix == ".bit" else "system.bit.bin"
    remote_path = f"{args.boot_mount}/{remote_name}"

    uenv_path = args.uenv
    if uenv_path is None and candidate_suffix == ".bit":
        uenv_path = DEFAULT_UENV
    if uenv_path is not None and not uenv_path.exists():
        raise FileNotFoundError(f"Missing uEnv override: {uenv_path}")

    payload = candidate_path.read_bytes()
    local_md5 = md5_bytes(payload)
    print(f"Local file: {candidate_path}")
    print(f"Remote file: {remote_path}")
    print(f"Local size: {len(payload)} bytes")
    print(f"Local md5 : {local_md5}")
    uenv_md5 = ""
    if uenv_path is not None:
        uenv_payload = uenv_path.read_bytes()
        uenv_md5 = md5_bytes(uenv_payload)
        print(f"uEnv file : {uenv_path}")
        print(f"uEnv md5  : {uenv_md5}")

    session = ParamikoSession(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        timeout_s=args.ssh_timeout_s,
    )
    try:
        print(run_remote_checked(
            session,
            f"mkdir -p {args.boot_mount} && "
            f"(mountpoint -q {args.boot_mount} || mount -t vfat /dev/mmcblk0p1 {args.boot_mount}) && "
            f"df -h {args.boot_mount}",
            context="mount FAT boot partition",
        ))
        session.upload_via_cat(remote_path, payload)
        if uenv_path is not None:
            session.upload_via_cat(f"{args.boot_mount}/uEnv.txt", uenv_payload)
        verification = run_remote_checked(
            session,
            f"sync && md5sum {remote_path} && ls -l {remote_path}",
            context="verify uploaded bitstream",
        )
        print(verification)
        remote_md5 = verification.split()[0]
        remote_uenv_md5 = ""
        if uenv_path is not None:
            uenv_verification = run_remote_checked(
                session,
                f"md5sum {args.boot_mount}/uEnv.txt && ls -l {args.boot_mount}/uEnv.txt",
                context="verify uploaded uEnv.txt",
            )
            print(uenv_verification)
            remote_uenv_md5 = uenv_verification.split()[0]
        else:
            remote_uenv_md5 = ""

        session.reboot()
    finally:
        session.close()

    wait_for_port_state(args.ssh_host, args.ssh_port, want_open=False, timeout_s=20.0)
    capture_uart_log(
        serial_port=args.serial_port,
        baudrate=args.baudrate,
        log_path=args.uart_log,
        capture_timeout_s=args.uart_capture_timeout_s,
    )
    print(f"UART log: {args.uart_log}")

    if not wait_for_port_state(
        args.ssh_host,
        args.ssh_port,
        want_open=True,
        timeout_s=args.reboot_timeout_s,
    ):
        raise RuntimeError("SSH did not return after reboot.")

    time.sleep(3.0)
    session = ParamikoSession(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        timeout_s=args.ssh_timeout_s,
    )
    try:
        dmesg_ad9361 = run_remote_checked(
            session,
            "dmesg | grep -i ad9361 || true",
            context="read AD9361 dmesg lines",
        )
        iio_devices_text = run_remote_checked(
            session,
            "ls /sys/bus/iio/devices",
            context="list IIO devices",
        )
    finally:
        session.close()

    iio_devices = [line.strip() for line in iio_devices_text.splitlines() if line.strip()]
    summary = ValidationSummary(
        local_path=str(candidate_path),
        remote_path=remote_path,
        local_md5=local_md5,
        remote_md5=remote_md5,
        uenv_path=str(uenv_path) if uenv_path is not None else "",
        uenv_md5=remote_uenv_md5,
        uart_log_path=str(args.uart_log),
        ad9361_initialized="successfully initialized" in dmesg_ad9361,
        iio_device_count=len(iio_devices),
        iio_devices=iio_devices,
        dmesg_ad9361=dmesg_ad9361,
    )

    print()
    print("Validation summary")
    for key, value in asdict(summary).items():
        print(f"{key}: {value}")

    if not summary.ad9361_initialized:
        return 1
    if summary.iio_device_count < 4:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
