# 
# Usage: To re-create this platform project launch xsct with below options.
# xsct F:\FPGA_Code\MyCore_7020_V3\AD936X_PS\platform\platform.tcl
# 
# OR launch xsct and run below command.
# source F:\FPGA_Code\MyCore_7020_V3\AD936X_PS\platform\platform.tcl
# 
# To create the platform in a different location, modify the -out option of "platform create" command.
# -out option specifies the output directory of the platform project.

platform create -name {platform}\
-hw {F:\FPGA_Code\MyCore_7020_V3\AD936X_PS\system_top.xsa}\
-proc {ps7_cortexa9_0} -os {standalone} -out {F:/FPGA_Code/MyCore_7020_V3/AD936X_PS}

platform write
platform generate -domains 
platform active {platform}
platform generate
platform generate
platform generate
platform generate
platform active {platform}
bsp reload
bsp setlib -name lwip211 -ver 1.5
bsp write
bsp reload
catch {bsp regenerate}
catch {bsp regenerate}
platform generate -domains standalone_domain 
platform active {platform}
domain create -name {freertos10_xilinx_ps7_cortexa9_0} -display-name {freertos10_xilinx_ps7_cortexa9_0} -os {freertos10_xilinx} -proc {ps7_cortexa9_0} -runtime {cpp} -arch {32-bit} -support-app {freertos_lwip_echo_server}
platform generate -domains 
platform write
domain active {zynq_fsbl}
domain active {standalone_domain}
domain active {freertos10_xilinx_ps7_cortexa9_0}
platform generate -quick
platform generate -domains freertos10_xilinx_ps7_cortexa9_0 
platform active {platform}
platform active {platform}
platform active {platform}
platform generate
platform active {platform}
platform config -updatehw {F:/FPGA_Code/MyCore_7020_V3/AD936X_PS/system_top.xsa}
domain active {standalone_domain}
bsp reload
catch {bsp regenerate}
domain active {zynq_fsbl}
bsp reload
catch {bsp regenerate}
platform generate -domains standalone_domain,zynq_fsbl 
platform clean
catch {bsp regenerate}
domain active {standalone_domain}
catch {bsp regenerate}
domain remove freertos10_xilinx_ps7_cortexa9_0
platform generate -domains 
platform write
platform generate
platform config -updatehw {F:/FPGA_Code/MyCore_7020_V3/AD936X_PS/system_top.xsa}
domain active {zynq_fsbl}
bsp reload
catch {bsp regenerate}
domain active {standalone_domain}
bsp reload
catch {bsp regenerate}
platform generate -domains standalone_domain,zynq_fsbl 
platform active {platform}
platform active {platform}
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform generate
platform active {platform}
platform config -updatehw {F:/FPGA_Code/7020_AD936X_SDR/AD936X_PS/system_top.xsa}
domain active {zynq_fsbl}
bsp reload
catch {bsp regenerate}
domain active {standalone_domain}
bsp reload
catch {bsp regenerate}
platform generate -domains standalone_domain,zynq_fsbl 
platform config -updatehw {F:/FPGA_Code/7020_AD936X_SDR/AD936X_PS/system_top.xsa}
domain active {zynq_fsbl}
bsp reload
catch {bsp regenerate}
domain active {standalone_domain}
bsp reload
catch {bsp regenerate}
platform generate -domains standalone_domain,zynq_fsbl 
platform config -updatehw {F:/FPGA_Code/7020_AD936X_SDR/AD936X_PS/system_top.xsa}
domain active {zynq_fsbl}
bsp reload
catch {bsp regenerate}
domain active {standalone_domain}
bsp reload
catch {bsp regenerate}
platform generate -domains standalone_domain,zynq_fsbl 
platform config -updatehw {F:/FPGA_Code/7020_AD936X_SDR/AD936X_PS/system_top.xsa}
domain active {zynq_fsbl}
bsp reload
catch {bsp regenerate}
domain active {standalone_domain}
bsp reload
catch {bsp regenerate}
platform generate -domains standalone_domain,zynq_fsbl 
domain active {zynq_fsbl}
catch {bsp regenerate}
domain active {standalone_domain}
catch {bsp regenerate}
platform generate -domains standalone_domain,zynq_fsbl 
platform generate
platform generate
