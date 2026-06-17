
# Loading additional proc with user specified bodies to compute parameter values.
source [file join [file dirname [file dirname [info script]]] gui/util_axis_fifo_v1_0.gtcl]

# Definitional proc to organize widgets for parameters.
proc init_gui { IPINST } {
  ipgui::add_param $IPINST -name "Component_Name"
  #Adding Page
  set AXI_Stream_FIFO [ipgui::add_page $IPINST -name "AXI Stream FIFO"]
  #Adding Group
  set Clock_Configuration [ipgui::add_group $IPINST -name "Clock Configuration" -parent ${AXI_Stream_FIFO}]
  set ASYNC_CLK [ipgui::add_param $IPINST -name "ASYNC_CLK" -parent ${Clock_Configuration} -widget comboBox]
  set_property tooltip {[ASYNC_CLK] If enabled the readn and write interface of the FIFO is asynchronous (its clocks are from different clock domain).} ${ASYNC_CLK}

  #Adding Group
  set Interface_Configuration [ipgui::add_group $IPINST -name "Interface Configuration" -parent ${AXI_Stream_FIFO}]
  set DATA_WIDTH [ipgui::add_param $IPINST -name "DATA_WIDTH" -parent ${Interface_Configuration} -widget comboBox]
  set_property tooltip {[DATA_WIDTH] Data width of the AXI stream interfaces.} ${DATA_WIDTH}
  set ADDRESS_WIDTH [ipgui::add_param $IPINST -name "ADDRESS_WIDTH" -parent ${Interface_Configuration}]
  set_property tooltip {[ADDRESS_WIDTH] Address width of the read and write address pointers. It defines the depth of the FIFO : DATA_WIDTH/8 * (2 ^ ADDRESS_WIDTH)} ${ADDRESS_WIDTH}
  set ALMOST_FULL_THRESHOLD [ipgui::add_param $IPINST -name "ALMOST_FULL_THRESHOLD" -parent ${Interface_Configuration}]
  set_property tooltip {[ALMOST_FULL_THRESHOLD] The offset between the almost full assertion and full assertion in number of FIFO words.} ${ALMOST_FULL_THRESHOLD}
  set ALMOST_EMPTY_THRESHOLD [ipgui::add_param $IPINST -name "ALMOST_EMPTY_THRESHOLD" -parent ${Interface_Configuration}]
  set_property tooltip {[ALMOST_EMPTY_THRESHOLD] The offset between the almost empty assertion and empty assertion in number of FIFO words.} ${ALMOST_EMPTY_THRESHOLD}
  set TLAST_EN [ipgui::add_param $IPINST -name "TLAST_EN" -parent ${Interface_Configuration}]
  set_property tooltip {[TLAST_EN] Enable the TLAST for the AXI stream interface, signaling packet boundaries.} ${TLAST_EN}
  set TKEEP_EN [ipgui::add_param $IPINST -name "TKEEP_EN" -parent ${Interface_Configuration}]
  set_property tooltip {[TKEEP_EN] Enable the TKEEP for the AXI stream interface, for data byte qualification for each AXIS beat.} ${TKEEP_EN}

  #Adding Group
  set Other_Features [ipgui::add_group $IPINST -name "Other Features" -parent ${AXI_Stream_FIFO}]
  set M_AXIS_REGISTERED [ipgui::add_param $IPINST -name "M_AXIS_REGISTERED" -parent ${Other_Features}]
  set_property tooltip {[M_AXIS_REGISTERED] Add an additional register stage to the master AXI stream data output.} ${M_AXIS_REGISTERED}
  set REMOVE_NULL_BEAT_EN [ipgui::add_param $IPINST -name "REMOVE_NULL_BEAT_EN" -parent ${Other_Features}]
  set_property tooltip {[REMOVE_NULL_BEAT_EN] Filteres out all the beats with a null TKEEP qualifier.} ${REMOVE_NULL_BEAT_EN}



}

proc update_PARAM_VALUE.REMOVE_NULL_BEAT_EN { PARAM_VALUE.REMOVE_NULL_BEAT_EN PARAM_VALUE.TKEEP_EN } {
	# Procedure called to update REMOVE_NULL_BEAT_EN when any of the dependent parameters in the arguments change
	
	set REMOVE_NULL_BEAT_EN ${PARAM_VALUE.REMOVE_NULL_BEAT_EN}
	set TKEEP_EN ${PARAM_VALUE.TKEEP_EN}
	set values(TKEEP_EN) [get_property value $TKEEP_EN]
	if { [gen_USERPARAMETER_REMOVE_NULL_BEAT_EN_ENABLEMENT $values(TKEEP_EN)] } {
		set_property enabled true $REMOVE_NULL_BEAT_EN
	} else {
		set_property enabled false $REMOVE_NULL_BEAT_EN
	}
}

proc validate_PARAM_VALUE.REMOVE_NULL_BEAT_EN { PARAM_VALUE.REMOVE_NULL_BEAT_EN } {
	# Procedure called to validate REMOVE_NULL_BEAT_EN
	return true
}

proc update_PARAM_VALUE.ADDRESS_WIDTH { PARAM_VALUE.ADDRESS_WIDTH } {
	# Procedure called to update ADDRESS_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.ADDRESS_WIDTH { PARAM_VALUE.ADDRESS_WIDTH } {
	# Procedure called to validate ADDRESS_WIDTH
	return true
}

proc update_PARAM_VALUE.ALMOST_EMPTY_THRESHOLD { PARAM_VALUE.ALMOST_EMPTY_THRESHOLD } {
	# Procedure called to update ALMOST_EMPTY_THRESHOLD when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.ALMOST_EMPTY_THRESHOLD { PARAM_VALUE.ALMOST_EMPTY_THRESHOLD } {
	# Procedure called to validate ALMOST_EMPTY_THRESHOLD
	return true
}

proc update_PARAM_VALUE.ALMOST_FULL_THRESHOLD { PARAM_VALUE.ALMOST_FULL_THRESHOLD } {
	# Procedure called to update ALMOST_FULL_THRESHOLD when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.ALMOST_FULL_THRESHOLD { PARAM_VALUE.ALMOST_FULL_THRESHOLD } {
	# Procedure called to validate ALMOST_FULL_THRESHOLD
	return true
}

proc update_PARAM_VALUE.ASYNC_CLK { PARAM_VALUE.ASYNC_CLK } {
	# Procedure called to update ASYNC_CLK when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.ASYNC_CLK { PARAM_VALUE.ASYNC_CLK } {
	# Procedure called to validate ASYNC_CLK
	return true
}

proc update_PARAM_VALUE.DATA_WIDTH { PARAM_VALUE.DATA_WIDTH } {
	# Procedure called to update DATA_WIDTH when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.DATA_WIDTH { PARAM_VALUE.DATA_WIDTH } {
	# Procedure called to validate DATA_WIDTH
	return true
}

proc update_PARAM_VALUE.M_AXIS_REGISTERED { PARAM_VALUE.M_AXIS_REGISTERED } {
	# Procedure called to update M_AXIS_REGISTERED when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.M_AXIS_REGISTERED { PARAM_VALUE.M_AXIS_REGISTERED } {
	# Procedure called to validate M_AXIS_REGISTERED
	return true
}

proc update_PARAM_VALUE.TKEEP_EN { PARAM_VALUE.TKEEP_EN } {
	# Procedure called to update TKEEP_EN when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.TKEEP_EN { PARAM_VALUE.TKEEP_EN } {
	# Procedure called to validate TKEEP_EN
	return true
}

proc update_PARAM_VALUE.TLAST_EN { PARAM_VALUE.TLAST_EN } {
	# Procedure called to update TLAST_EN when any of the dependent parameters in the arguments change
}

proc validate_PARAM_VALUE.TLAST_EN { PARAM_VALUE.TLAST_EN } {
	# Procedure called to validate TLAST_EN
	return true
}


proc update_MODELPARAM_VALUE.DATA_WIDTH { MODELPARAM_VALUE.DATA_WIDTH PARAM_VALUE.DATA_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.DATA_WIDTH}] ${MODELPARAM_VALUE.DATA_WIDTH}
}

proc update_MODELPARAM_VALUE.ADDRESS_WIDTH { MODELPARAM_VALUE.ADDRESS_WIDTH PARAM_VALUE.ADDRESS_WIDTH } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.ADDRESS_WIDTH}] ${MODELPARAM_VALUE.ADDRESS_WIDTH}
}

proc update_MODELPARAM_VALUE.ASYNC_CLK { MODELPARAM_VALUE.ASYNC_CLK PARAM_VALUE.ASYNC_CLK } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.ASYNC_CLK}] ${MODELPARAM_VALUE.ASYNC_CLK}
}

proc update_MODELPARAM_VALUE.M_AXIS_REGISTERED { MODELPARAM_VALUE.M_AXIS_REGISTERED PARAM_VALUE.M_AXIS_REGISTERED } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.M_AXIS_REGISTERED}] ${MODELPARAM_VALUE.M_AXIS_REGISTERED}
}

proc update_MODELPARAM_VALUE.ALMOST_EMPTY_THRESHOLD { MODELPARAM_VALUE.ALMOST_EMPTY_THRESHOLD PARAM_VALUE.ALMOST_EMPTY_THRESHOLD } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.ALMOST_EMPTY_THRESHOLD}] ${MODELPARAM_VALUE.ALMOST_EMPTY_THRESHOLD}
}

proc update_MODELPARAM_VALUE.ALMOST_FULL_THRESHOLD { MODELPARAM_VALUE.ALMOST_FULL_THRESHOLD PARAM_VALUE.ALMOST_FULL_THRESHOLD } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.ALMOST_FULL_THRESHOLD}] ${MODELPARAM_VALUE.ALMOST_FULL_THRESHOLD}
}

proc update_MODELPARAM_VALUE.TLAST_EN { MODELPARAM_VALUE.TLAST_EN PARAM_VALUE.TLAST_EN } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.TLAST_EN}] ${MODELPARAM_VALUE.TLAST_EN}
}

proc update_MODELPARAM_VALUE.TKEEP_EN { MODELPARAM_VALUE.TKEEP_EN PARAM_VALUE.TKEEP_EN } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.TKEEP_EN}] ${MODELPARAM_VALUE.TKEEP_EN}
}

proc update_MODELPARAM_VALUE.REMOVE_NULL_BEAT_EN { MODELPARAM_VALUE.REMOVE_NULL_BEAT_EN PARAM_VALUE.REMOVE_NULL_BEAT_EN } {
	# Procedure called to set VHDL generic/Verilog parameter value(s) based on TCL parameter value
	set_property value [get_property value ${PARAM_VALUE.REMOVE_NULL_BEAT_EN}] ${MODELPARAM_VALUE.REMOVE_NULL_BEAT_EN}
}

