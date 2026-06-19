function ws = lab_4_4_prepare_bpsk_simulink_workspace(varargin)
%LAB_4_4_PREPARE_BPSK_SIMULINK_WORKSPACE Prepare shared workspace variables.
%
% This helper bridges the Block 11 BPSK handoff package into Simulink and
% also prepares the ideal BER-vs-SNR data stream for the AWGN reference model.

parser = inputParser;
parser.addParameter('snr_db', 8, @(x) isnumeric(x) && isscalar(x));
parser.addParameter('frame_bits', 200000, @(x) isnumeric(x) && isscalar(x) && x > 0);
parser.addParameter('seed', 4404, @(x) isnumeric(x) && isscalar(x));
parser.parse(varargin{:});
cfgRun = parser.Results;

thisDir = fileparts(mfilename('fullpath'));
blockDir = fileparts(thisDir);
blocksDir = fileparts(blockDir);
rootDir = fileparts(blocksDir);
packageDir = fullfile(rootDir, 'blocks', 'block_11_integrated_sdr_project', 'assets', 'end_to_end_bpsk_reference');
pythonScript = fullfile(rootDir, 'blocks', 'block_11_integrated_sdr_project', 'python', 'end_to_end_bpsk_reference.py');

required = {
    fullfile(packageDir, 'config.json')
    fullfile(packageDir, 'tx_bits.txt')
    fullfile(packageDir, 'tx_symbols_q15.txt')
    fullfile(packageDir, 'rrc_taps_q15.txt')
    fullfile(packageDir, 'sample_plan.json')
    fullfile(packageDir, 'end_to_end_bpsk_reference_v1.ci16')
    fullfile(packageDir, 'end_to_end_bpsk_reference_v1_tx_reference.ci16')
};

missing = false;
for k = 1:numel(required)
    if exist(required{k}, 'file') ~= 2
        missing = true;
        break;
    end
end

if missing
    [status, output] = system(sprintf('python "%s"', pythonScript));
    if status ~= 0
        error('Failed to regenerate Block 11 BPSK package:\n%s', output);
    end
end

cfg = jsondecode(fileread(fullfile(packageDir, 'config.json')));
samplePlan = jsondecode(fileread(fullfile(packageDir, 'sample_plan.json')));
symbolPairsQ15 = load(fullfile(packageDir, 'tx_symbols_q15.txt'));
tapsQ15Int = int16(load(fullfile(packageDir, 'rrc_taps_q15.txt')));
capture = read_ci16(fullfile(packageDir, sprintf('%s.ci16', cfg.dataset_id)));

q15Scale = 2^15;
txSymbolsQ15 = complex(double(symbolPairsQ15(:, 1)) ./ q15Scale, double(symbolPairsQ15(:, 2)) ./ q15Scale);
rrcTapsQ15 = double(tapsQ15Int(:)) ./ q15Scale;

upsampled = upsample_complex(txSymbolsQ15, cfg.samples_per_symbol);
upsampled = [upsampled; complex(zeros(numel(rrcTapsQ15) - 1, 1))];
txFilterReference = conv(upsampled(1:end-numel(rrcTapsQ15)+1), rrcTapsQ15);
txGain = cfg.tx_amplitude / max(abs(txFilterReference));
txGainQ15 = double(int16(clip(round(txGain * 32767.0), -32768, 32767))) / q15Scale;

t = (0:numel(capture)-1).' ./ cfg.sample_rate_hz;
rxCorrected = capture .* exp(-1j .* (2.0 .* pi .* cfg.cfo_hz .* t + cfg.phase_offset_rad));
rxCorrected = [rxCorrected; complex(zeros(numel(rrcTapsQ15) - 1, 1))];
rxMatchedReference = conv(rxCorrected(1:end-numel(rrcTapsQ15)+1), rrcTapsQ15);

fixedLen = max(numel(upsampled), numel(rxCorrected));
txInputPadded = pad_to_length(upsampled, fixedLen);
rxInputPadded = pad_to_length(rxCorrected, fixedLen);

lab44FixedChainStopTime = fixedLen - 1;
lab44TxUpsampledTs = timeseries(txInputPadded, (0:fixedLen-1).');
lab44RxCorrectedTs = timeseries(rxInputPadded, (0:fixedLen-1).');

rng(cfgRun.seed);
berBits = uint8(rand(cfgRun.frame_bits, 1) > 0.5);
berNoise = randn(cfgRun.frame_bits, 1);
noiseSigma = sqrt(1.0 / (2.0 * 10.^(cfgRun.snr_db / 10.0)));
lab44BerBitsTs = timeseries(double(berBits), (0:cfgRun.frame_bits-1).');
lab44BerNoiseTs = timeseries(berNoise, (0:cfgRun.frame_bits-1).');

ws = struct();
ws.cfg = cfg;
ws.sample_plan = samplePlan;
ws.tx_input = txInputPadded;
ws.rx_input = rxInputPadded;
ws.tx_reference = txFilterReference * txGainQ15;
ws.rx_reference = rxMatchedReference;
ws.rrc_taps_q15 = rrcTapsQ15;
ws.tx_gain = txGainQ15;
ws.bits = berBits;
ws.noise = berNoise;
ws.noise_sigma = noiseSigma;
ws.snr_db = cfgRun.snr_db;
ws.frame_bits = cfgRun.frame_bits;

assignin('base', 'lab44_tx_upsampled_ts', lab44TxUpsampledTs);
assignin('base', 'lab44_rx_corrected_ts', lab44RxCorrectedTs);
assignin('base', 'lab44_rrc_taps_q15', rrcTapsQ15);
assignin('base', 'lab44_tx_gain', txGainQ15);
assignin('base', 'lab44_fixed_chain_stop_time', lab44FixedChainStopTime);
assignin('base', 'lab44_fixed_tx_reference', ws.tx_reference);
assignin('base', 'lab44_fixed_rx_reference', ws.rx_reference);
assignin('base', 'lab44_ber_bits_ts', lab44BerBitsTs);
assignin('base', 'lab44_ber_noise_ts', lab44BerNoiseTs);
assignin('base', 'lab44_ber_noise_sigma', noiseSigma);
assignin('base', 'lab44_ber_bits_vector', berBits);
assignin('base', 'lab44_ber_stop_time', cfgRun.frame_bits - 1);
assignin('base', 'lab44_ber_snr_db', cfgRun.snr_db);
end

function x = read_ci16(path)
fid = fopen(path, 'rb');
if fid < 0
    error('Cannot open %s', path);
end
raw = fread(fid, inf, 'int16=>double');
fclose(fid);
if mod(numel(raw), 2) ~= 0
    error('Invalid CI16 file: %s', path);
end
i = raw(1:2:end) ./ 32768.0;
q = raw(2:2:end) ./ 32768.0;
x = complex(i, q);
end

function y = upsample_complex(symbols, sps)
y = complex(zeros(numel(symbols) * sps, 1));
y(1:sps:end) = symbols(:);
end

function y = pad_to_length(x, targetLength)
y = complex(zeros(targetLength, 1));
y(1:numel(x)) = x(:);
end

function y = clip(x, lo, hi)
y = min(max(x, lo), hi);
end
