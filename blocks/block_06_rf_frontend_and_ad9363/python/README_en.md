# Python Scripts and Automation

## Purpose
This folder is intended for reproducible processing scripts, measurement automation, and quick hypothesis checks for Block 6 “RF Frontend and AD9363”.

## What should be stored here
- materials that directly support the block topics: RX and TX chain structure; levels, gain staging, and dynamic range; LO frequencies, bandwidth, and filters;
- files that can be reused in a laboratory task, demonstration, or mini-project;
- short notes describing how to run the material, where the data comes from, and what result is expected.

## Minimum meaningful content
- one reproducible example for a key idea of the block;
- one artifact or artifact set suitable for insertion into a report;
- one note that connects the folder contents with the engineering logic of the course.

## Suggested file names
- `rf_frontend_analysis.py`
- `gain_plan_sweep.py`
- `ad9363_visualization.py`
- `lab_6_3_probe_iio_context.py`

## Quality criteria
- files should be reproducible and understandable without oral explanation;
- experiment parameters, tool versions, and limits should be documented next to the material;
- the materials should help the student reach at least one outcome of the block: RF chain level map, AD9363 settings description.

## Included host-side probe

The folder now includes `lab_6_3_probe_iio_context.py`, a small host-side probe
for network IIO targets such as `ip:192.168.40.1`.

Example:

```bash
python blocks/block_06_rf_frontend_and_ad9363/python/lab_6_3_probe_iio_context.py \
  --uri ip:192.168.40.1 \
  --json-out docs/assets/lab63_zynq_iio_probe.json
```

On Windows, the script can auto-discover `libiio.dll` from the default
`IIO Oscilloscope` install path.
