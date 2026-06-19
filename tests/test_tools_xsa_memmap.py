from __future__ import annotations

import sys
import zipfile
from io import BytesIO
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from inspect_xsa_memmap import filter_memranges, parse_memranges_text, read_memranges  # noqa: E402


def test_parse_memranges_text_extracts_and_sorts_entries() -> None:
    text = """
    <HWH>
      <MEMRANGE INSTANCE="axi_dmac" BASEVALUE="0x7C400000" HIGHVALUE="0x7C400FFF"
                ADDRESSBLOCK="axi_lite" MEMTYPE="REGISTER" MASTERBUSINTERFACE="M_AXI_GP0"
                SLAVEBUSINTERFACE="s_axi" BASENAME="C_BASEADDR" HIGHNAME="C_HIGHADDR" />
      <MEMRANGE INSTANCE="axi_ctrl" BASEVALUE="0x43C00000" HIGHVALUE="0x43C0FFFF"
                ADDRESSBLOCK="s_axi_reg" MEMTYPE="REGISTER" MASTERBUSINTERFACE="M_AXI_GP0"
                SLAVEBUSINTERFACE="S_AXI" BASENAME="C_BASEADDR" HIGHNAME="C_HIGHADDR" />
    </HWH>
    """

    memranges = parse_memranges_text(text)

    assert [entry.instance for entry in memranges] == ["axi_ctrl", "axi_dmac"]
    assert memranges[0].base_addr == 0x43C00000
    assert memranges[0].high_addr == 0x43C0FFFF
    assert memranges[1].slave_bus_interface == "s_axi"


def test_read_memranges_from_reference_xsa_contains_ad9361_windows() -> None:
    export_path = (
        Path(__file__).resolve().parents[1]
        / "hardware"
        / "7020_ad936x_sdr"
        / "ps"
        / "ad936x_no_os_reference"
        / "system_top.xsa"
    )

    memranges = read_memranges(export_path)
    by_instance = {entry.instance: entry for entry in memranges}

    assert by_instance["axi_ad9361"].base_addr == 0x79020000
    assert by_instance["axi_ad9361_adc_dma"].base_addr == 0x7C400000
    assert by_instance["axi_ad9361_dac_dma"].base_addr == 0x7C420000


def test_filter_memranges_matches_case_insensitive_substrings() -> None:
    text = """
    <HWH>
      <MEMRANGE INSTANCE="axi_ad9361" BASEVALUE="0x79020000" HIGHVALUE="0x7902FFFF" />
      <MEMRANGE INSTANCE="axi_ad9361_adc_dma" BASEVALUE="0x7C400000" HIGHVALUE="0x7C400FFF" />
      <MEMRANGE INSTANCE="bpsk_zynq_ber_axi_lite" BASEVALUE="0x43C00000" HIGHVALUE="0x43C0FFFF" />
    </HWH>
    """

    memranges = parse_memranges_text(text)
    filtered = filter_memranges(memranges, ["bpsk", "axi"])

    assert [entry.instance for entry in filtered] == ["bpsk_zynq_ber_axi_lite"]


def test_read_memranges_from_outer_zip_with_nested_xsa(tmp_path: Path) -> None:
    hwh_text = """
    <HWH>
      <MEMRANGE INSTANCE="bpsk_zynq_ber_axi_lite" BASEVALUE="0x43C00000" HIGHVALUE="0x43C0FFFF" />
    </HWH>
    """.strip()

    nested_xsa_bytes = BytesIO()
    with zipfile.ZipFile(nested_xsa_bytes, "w") as nested_xsa:
        nested_xsa.writestr("hw/design_1.hwh", hwh_text)

    outer_zip = tmp_path / "vendor_bundle.zip"
    with zipfile.ZipFile(outer_zip, "w") as archive:
        archive.writestr("platform/export/hw/system_top.xsa", nested_xsa_bytes.getvalue())

    memranges = read_memranges(outer_zip)

    assert len(memranges) == 1
    assert memranges[0].instance == "bpsk_zynq_ber_axi_lite"
    assert memranges[0].base_addr == 0x43C00000
