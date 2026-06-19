function lab_4_4_run_bpsk_simulink_models()
%LAB_4_4_RUN_BPSK_SIMULINK_MODELS Generate, simulate and validate models.

thisDir = fileparts(mfilename('fullpath'));
blockDir = fileparts(thisDir);
rootDir = fileparts(fileparts(blockDir));
assetDir = fullfile(rootDir, 'docs', 'assets');
simDir = fullfile(blockDir, 'simulink');

if exist(assetDir, 'dir') ~= 7
    mkdir(assetDir);
end

lab_4_4_generate_bpsk_simulink_models();

ws = lab_4_4_prepare_bpsk_simulink_workspace('snr_db', 8, 'frame_bits', 200000, 'seed', 4404);
fixedModel = fullfile(simDir, 'lab_4_4_bpsk_fixed_point_chain.slx');
fixedOut = sim(fixedModel, 'ReturnWorkspaceOutputs', 'on');

txShaped = extract_timeseries(fixedOut, 'lab44_tx_chain_out');
rxMatched = extract_timeseries(fixedOut, 'lab44_rx_chain_out');
txRef = double(ws.tx_reference(:));
rxRef = double(ws.rx_reference(:));

txLen = min(numel(txShaped), numel(txRef));
rxLen = min(numel(rxMatched), numel(rxRef));
txRmse = sqrt(mean(abs(txShaped(1:txLen) - txRef(1:txLen)) .^ 2));
rxRmse = sqrt(mean(abs(rxMatched(1:rxLen) - rxRef(1:rxLen)) .^ 2));

figure('Color', 'w');
shown = min(260, txLen);
plot(0:shown-1, real(txRef(1:shown)), 'DisplayName', 'reference'); hold on;
plot(0:shown-1, real(txShaped(1:shown)), '--', 'DisplayName', 'Simulink');
grid on;
xlabel('Sample index'); ylabel('Amplitude');
title('Lab 4.4 - Simulink TX pulse shaping vs reference');
legend('Location', 'best');
saveas(gcf, fullfile(assetDir, 'lab44_bpsk_simulink_tx_overlay_matlab.png'));

figure('Color', 'w');
shownRx = min(260, rxLen);
plot(0:shownRx-1, real(rxRef(1:shownRx)), 'DisplayName', 'reference'); hold on;
plot(0:shownRx-1, real(rxMatched(1:shownRx)), '--', 'DisplayName', 'Simulink');
grid on;
xlabel('Sample index'); ylabel('Amplitude');
title('Lab 4.4 - Simulink matched filter vs reference');
legend('Location', 'best');
saveas(gcf, fullfile(assetDir, 'lab44_bpsk_simulink_rx_overlay_matlab.png'));

berModel = fullfile(simDir, 'lab_4_4_bpsk_ideal_ber_awgn.slx');
snrDbAxis = 0:1:10;
berSim = zeros(size(snrDbAxis));
berTheory = 0.5 .* erfc(sqrt(10 .^ (snrDbAxis ./ 10.0)));

for idx = 1:numel(snrDbAxis)
    lab_4_4_prepare_bpsk_simulink_workspace('snr_db', snrDbAxis(idx), 'frame_bits', 200000, 'seed', 5500 + idx);
    simOut = sim(berModel, 'ReturnWorkspaceOutputs', 'on');
    rxBits = uint8(extract_timeseries(simOut, 'lab44_ber_rx_bits') > 0.5);
    txBits = uint8(evalin('base', 'lab44_ber_bits_vector(:)'));
    compared = min(numel(txBits), numel(rxBits));
    berSim(idx) = mean(txBits(1:compared) ~= rxBits(1:compared));
end

berPlot = max(berSim, 0.5 / 200000);
theoryAxisFine = 0:0.1:10;
theoryFine = 0.5 .* erfc(sqrt(10 .^ (theoryAxisFine ./ 10.0)));

figure('Color', 'w');
semilogy(theoryAxisFine, theoryFine, 'LineWidth', 1.8, 'DisplayName', 'theory'); hold on;
semilogy(snrDbAxis, berPlot, 'o-', 'LineWidth', 1.4, 'DisplayName', 'Simulink Monte Carlo');
grid on;
xlabel('SNR / E_b/N_0, dB');
ylabel('BER');
title('Lab 4.4 - Ideal BPSK BER vs SNR');
legend('Location', 'southwest');
saveas(gcf, fullfile(assetDir, 'lab44_bpsk_ideal_ber_vs_snr_matlab.png'));

metrics = struct( ...
    'tx_rmse', txRmse, ...
    'rx_rmse', rxRmse, ...
    'snr_db_axis', snrDbAxis, ...
    'ber_sim', berSim, ...
    'ber_theory', berTheory, ...
    'max_abs_ber_delta', max(abs(berSim - berTheory)) ...
);

fid = fopen(fullfile(assetDir, 'lab44_bpsk_simulink_metrics.json'), 'w');
fwrite(fid, jsonencode(metrics, PrettyPrint=true), 'char');
fclose(fid);

fprintf('Lab 4.4 - BPSK Simulink models\n');
fprintf('TX/RX RMSE vs reference: %.6e / %.6e\n', txRmse, rxRmse);
fprintf('Max BER delta vs theory: %.6e\n', metrics.max_abs_ber_delta);
fprintf('Models: %s\n', simDir);
fprintf('Figures saved to: %s\n', assetDir);
end

function data = extract_timeseries(simOut, varName)
value = simOut.get(varName);
if isa(value, 'timeseries')
    data = value.Data;
elseif isstruct(value) && isfield(value, 'signals')
    data = value.signals.values;
else
    data = value;
end
data = double(data(:));
end
