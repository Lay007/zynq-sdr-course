#!/usr/bin/env python3
"""Validate a boot-time FPGA payload through manual UART-driven U-Boot commands.

This helper is for `.bit.bin` payloads that must be tested with:

1. reboot the board;
2. stop U-Boot autoboot over UART;
3. run `load mmc ...` plus `fpga load ...` manually;
4. boot Linux with `bootm`;
5. verify whether AD9361 and the expected IIO devices return.
"""

from __future__ import annotations

import argparse
import shlex
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from validate_clean_boot_overlay import (
    DEFAULT_BAUDRATE,
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_SERIAL_PORT,
    DEFAULT_USER,
    REMOTE_MOUNT,
    ParamikoSession,
    ensure_remote_free_bytes,
    md5_bytes,
    remote_file_size_or_zero,
    run_remote_checked,
    wait_for_port_state,
)


DEFAULT_UART_LOG = Path(__file__).resolve().parent / "last_manual_uart_fpga_load.log"
U_BOOT_PROMPT = "Pluto> "
LOGIN_PATTERNS = ("pluto login:", "login:")


@dataclass(frozen=True)
class ManualValidationSummary:
    local_path: str
    remote_path: str
    local_md5: str
    remote_md5: str
    fpga_operation: str
    fpga_command_output: str
    fpga_load_accepted: bool
    uart_log_path: str
    ad9361_initialized: bool
    iio_device_count: int
    iio_devices: list[str]
    dmesg_ad9361: str


class UartConsole:
    def __init__(self, *, serial_port: str, baudrate: int) -> None:
        try:
            import serial
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "This script requires pyserial. Install dependencies from requirements.txt."
            ) from exc

        self._serial = serial.Serial(serial_port, baudrate, timeout=0.1)
        self._chunks: list[str] = []

    def close(self) -> None:
        self._serial.close()

    @property
    def text(self) -> str:
        return "".join(self._chunks)

    def write(self, text: str) -> None:
        self._serial.write(text.encode("ascii"))
        self._serial.flush()

    def reset_input_buffer(self) -> None:
        self._serial.reset_input_buffer()

    def _append(self, text: str) -> None:
        self._chunks.append(text)

    def read_until(self, patterns: tuple[str, ...], *, timeout_s: float) -> str:
        deadline = time.time() + timeout_s
        collected = ""
        while time.time() < deadline:
            data = self._serial.read(4096)
            if not data:
                continue
            text = data.decode("utf-8", errors="replace")
            self._append(text)
            collected += text
            if any(pattern in collected for pattern in patterns):
                return collected
        raise TimeoutError(f"Timed out waiting for UART patterns: {patterns}")

    def stop_autoboot(self, *, timeout_s: float = 45.0) -> None:
        seen_uboot = False
        uboot_seen_at = 0.0
        last_send_at = 0.0
        deadline = time.time() + timeout_s
        collected = ""
        while time.time() < deadline:
            data = self._serial.read(4096)
            if data:
                text = data.decode("utf-8", errors="replace")
                self._append(text)
                collected += text
                if "U-Boot PlutoSDR" in collected and not seen_uboot:
                    seen_uboot = True
                    uboot_seen_at = time.time()
                if U_BOOT_PROMPT in collected:
                    return
            if (
                seen_uboot
                and time.time() - uboot_seen_at < 12.0
                and time.time() - last_send_at > 0.05
            ):
                self._serial.write(b" ")
                self._serial.flush()
                last_send_at = time.time()
        raise TimeoutError("Failed to stop U-Boot autoboot and reach the Pluto prompt.")

    def send_command(self, command: str, *, timeout_s: float) -> str:
        self.write(command + "\n")
        return self.read_until((U_BOOT_PROMPT,), timeout_s=timeout_s)

    def boot_linux(self, *, timeout_s: float) -> str:
        return self.read_until(LOGIN_PATTERNS, timeout_s=timeout_s)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate",
        type=Path,
        help="Optional local bitstream payload to upload before reboot. Use for .bit.bin or other fpga-loadable files.",
    )
    parser.add_argument(
        "--remote-name",
        help="Filename on the FAT root used by U-Boot load mmc. Defaults to the local candidate basename.",
    )
    parser.add_argument(
        "--fpga-operation",
        default="load",
        choices=("load", "loadb"),
        help="U-Boot fpga subcommand to run after load mmc.",
    )
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
    parser.add_argument("--login-timeout-s", type=float, default=240.0)
    return parser


def infer_remote_name(candidate: Path | None, remote_name: str | None) -> str:
    if remote_name:
        return remote_name
    if candidate is not None:
        return candidate.name
    raise ValueError("Pass either --candidate or --remote-name.")


def upload_candidate(
    *,
    candidate_path: Path,
    remote_path: str,
    host: str,
    user: str,
    password: str,
    port: int,
    timeout_s: float,
    boot_mount: str,
) -> tuple[str, str]:
    payload = candidate_path.read_bytes()
    local_md5 = md5_bytes(payload)
    session = ParamikoSession(
        host=host,
        user=user,
        password=password,
        port=port,
        timeout_s=timeout_s,
    )
    try:
        quoted_mount = shlex.quote(boot_mount)
        run_remote_checked(
            session,
            f"mkdir -p {quoted_mount} && "
            f"(mountpoint -q {quoted_mount} || mount -t vfat /dev/mmcblk0p1 {quoted_mount})",
            context="mount FAT boot partition",
        )
        additional_bytes = max(
            0,
            len(payload) - remote_file_size_or_zero(session, remote_path),
        )
        ensure_remote_free_bytes(
            session,
            boot_mount=boot_mount,
            required_bytes=additional_bytes,
        )
        session.upload_bytes(remote_path, payload)
        verification = run_remote_checked(
            session,
            f"sync && md5sum {shlex.quote(remote_path)} && ls -l {shlex.quote(remote_path)}",
            context="verify uploaded candidate",
        )
    finally:
        session.close()
    remote_md5 = verification.split()[0]
    return local_md5, remote_md5


def collect_post_boot_summary(
    *,
    host: str,
    user: str,
    password: str,
    port: int,
    timeout_s: float,
) -> tuple[str, list[str]]:
    session = ParamikoSession(
        host=host,
        user=user,
        password=password,
        port=port,
        timeout_s=timeout_s,
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
    return dmesg_ad9361, iio_devices


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    candidate_path = args.candidate.resolve() if args.candidate else None
    if candidate_path is not None and not candidate_path.exists():
        raise FileNotFoundError(f"Missing local candidate: {candidate_path}")

    remote_name = infer_remote_name(candidate_path, args.remote_name)
    remote_path = f"{args.boot_mount}/{remote_name}"

    local_md5 = ""
    remote_md5 = ""
    if candidate_path is not None:
        local_md5, remote_md5 = upload_candidate(
            candidate_path=candidate_path,
            remote_path=remote_path,
            host=args.ssh_host,
            user=args.ssh_user,
            password=args.ssh_password,
            port=args.ssh_port,
            timeout_s=args.ssh_timeout_s,
            boot_mount=args.boot_mount,
        )

    console = UartConsole(serial_port=args.serial_port, baudrate=args.baudrate)
    try:
        session = ParamikoSession(
            host=args.ssh_host,
            user=args.ssh_user,
            password=args.ssh_password,
            port=args.ssh_port,
            timeout_s=args.ssh_timeout_s,
        )
        try:
            console.reset_input_buffer()
            session.reboot()
        finally:
            session.close()

        console.stop_autoboot()
        console.send_command(
            f"load mmc 0 0x100000 {remote_name}",
            timeout_s=120.0,
        )
        fpga_command_output = console.send_command(
            f"fpga {args.fpga_operation} 0 0x100000 ${{filesize}}",
            timeout_s=120.0,
        )
        console.send_command("load mmc 0 0x2080000 uImage", timeout_s=120.0)
        console.send_command("load mmc 0 0x2000000 devicetree.dtb", timeout_s=120.0)
        console.send_command("load mmc 0 0x4000000 uramdisk.image.gz", timeout_s=120.0)
        console.send_command("fdt addr 0x2000000", timeout_s=30.0)
        console.send_command("fdt rm /fpga-axi/i2c@41600000", timeout_s=30.0)
        console.send_command("fdt rm /fpga-axi/mwipcore@43c00000", timeout_s=30.0)
        console.write("bootm 0x2080000 0x4000000 0x2000000\n")
        console.boot_linux(timeout_s=args.login_timeout_s)
    finally:
        args.uart_log.write_text(console.text, encoding="utf-8", errors="replace")
        console.close()

    if not wait_for_port_state(
        args.ssh_host,
        args.ssh_port,
        want_open=True,
        timeout_s=args.reboot_timeout_s,
    ):
        raise RuntimeError("SSH did not return after manual U-Boot boot sequence.")

    time.sleep(3.0)
    dmesg_ad9361, iio_devices = collect_post_boot_summary(
        host=args.ssh_host,
        user=args.ssh_user,
        password=args.ssh_password,
        port=args.ssh_port,
        timeout_s=args.ssh_timeout_s,
    )

    fpga_load_accepted = "Bitstream is not validated yet" not in fpga_command_output and "Usage:" not in fpga_command_output
    summary = ManualValidationSummary(
        local_path=str(candidate_path) if candidate_path is not None else "",
        remote_path=remote_path,
        local_md5=local_md5,
        remote_md5=remote_md5,
        fpga_operation=args.fpga_operation,
        fpga_command_output=fpga_command_output.strip(),
        fpga_load_accepted=fpga_load_accepted,
        uart_log_path=str(args.uart_log),
        ad9361_initialized="successfully initialized" in dmesg_ad9361,
        iio_device_count=len(iio_devices),
        iio_devices=iio_devices,
        dmesg_ad9361=dmesg_ad9361,
    )

    print("Manual UART FPGA-load summary")
    for key, value in asdict(summary).items():
        print(f"{key}: {value}")

    if not summary.fpga_load_accepted:
        return 1
    if not summary.ad9361_initialized:
        return 1
    if summary.iio_device_count < 4:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
