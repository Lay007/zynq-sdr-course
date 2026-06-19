function lab_4_4_ensure_bpsk_simulink_workspace()
%LAB_4_4_ENSURE_BPSK_SIMULINK_WORKSPACE Populate base workspace on demand.
%
% The generated .slx files can be opened and simulated directly. When the
% runner already prepared a specific workspace (for example, an SNR sweep),
% this helper must not overwrite it.

requiredVars = {
    'lab44_tx_upsampled_ts'
    'lab44_rx_corrected_ts'
    'lab44_rrc_taps_q15'
    'lab44_tx_gain'
    'lab44_fixed_chain_stop_time'
    'lab44_ber_bits_ts'
    'lab44_ber_noise_ts'
    'lab44_ber_noise_sigma'
    'lab44_ber_bits_vector'
    'lab44_ber_stop_time'
};

for idx = 1:numel(requiredVars)
    existsInBase = evalin('base', sprintf('exist(''%s'', ''var'')', requiredVars{idx}));
    if existsInBase ~= 1
        lab_4_4_prepare_bpsk_simulink_workspace();
        return;
    end
end
end
