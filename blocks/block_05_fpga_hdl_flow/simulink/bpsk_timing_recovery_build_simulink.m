function bpsk_timing_recovery_build_simulink()
%BPSK_TIMING_RECOVERY_BUILD_SIMULINK  Build a reproducible Simulink model of the
%   Lab 5.8b Gardner symbol timing-recovery loop (companion to the Python/MATLAB
%   reference models and the HDL bpsk_symbol_timing_recovery.v).
%
%   The model streams a time-drifted (SPS=8.03) matched-filter sample per discrete
%   step into a MATLAB Function block that implements the bit-exact fixed-point
%   loop (decrementing NCO + linear interpolator + sign-Gardner TED + PI filter).
%   The block is written in the HDL-Coder subset, so it doubles as the Simulink
%   path to the same RTL. To Workspace logs the recovered symbols / valids.
%
%   Run this once to (re)generate simulink/bpsk_timing_recovery.slx. Requires
%   Simulink; the .slx is a generated artifact (the build script is the source).

    prepare_workspace();

    thisDir = fileparts(mfilename('fullpath'));
    modelName = 'bpsk_timing_recovery';
    modelPath = fullfile(thisDir, [modelName '.slx']);

    if bdIsLoaded(modelName), close_system(modelName, 0); end
    if exist(modelPath, 'file') == 4, delete(modelPath); end
    new_system(modelName);
    open_system(modelName);

    set_param(modelName, 'Solver', 'FixedStepDiscrete', 'FixedStep', '1', ...
        'StopTime', 'tr_stop_time', 'InitFcn', 'bpsk_timing_recovery_build_simulink_workspace;');

    % --- matched-filter sample stream (one 16-bit signed sample per step) ---
    add_block('simulink/Sources/From Workspace', [modelName '/MF Input'], ...
        'Position', [40 60 180 100], 'VariableName', 'tr_mf_ts', ...
        'SampleTime', '1', 'Interpolate', 'off');

    % --- start gate: in_valid is high for the whole burst ---
    add_block('simulink/Sources/Constant', [modelName '/in_valid'], ...
        'Position', [40 130 180 170], 'Value', '1', ...
        'OutDataTypeStr', 'boolean', 'SampleTime', '1');

    % --- the timing-recovery loop as a HDL-Coder-friendly MATLAB Function block ---
    fcnBlock = [modelName '/Timing Recovery'];
    add_block('simulink/User-Defined Functions/MATLAB Function', fcnBlock, ...
        'Position', [280 55 520 175]);
    set_matlab_function(fcnBlock, timing_recovery_step_code());

    add_block('simulink/Sinks/To Workspace', [modelName '/Symbol Out'], ...
        'Position', [620 55 760 95], 'VariableName', 'tr_symbol_out', 'SaveFormat', 'Timeseries');
    add_block('simulink/Sinks/To Workspace', [modelName '/Valid Out'], ...
        'Position', [620 135 760 175], 'VariableName', 'tr_valid_out', 'SaveFormat', 'Timeseries');

    add_line(modelName, 'MF Input/1', 'Timing Recovery/1', 'autorouting', 'on');
    add_line(modelName, 'in_valid/1', 'Timing Recovery/2', 'autorouting', 'on');
    add_line(modelName, 'Timing Recovery/1', 'Symbol Out/1', 'autorouting', 'on');
    add_line(modelName, 'Timing Recovery/2', 'Valid Out/1', 'autorouting', 'on');

    add_block('simulink/Model-Wide Utilities/Model Info', [modelName '/Note'], ...
        'Position', [280 210 760 320], ...
        'Text', sprintf(['Lab 5.8b BPSK Gardner timing recovery.\n' ...
        'Bit-exact with bpsk_symbol_timing_recovery.v and the Python/MATLAB models.\n' ...
        'Drifted SPS=8.03 input -> recovered symbols at BER 0 where a fixed-phase\n' ...
        'decimator drifts off. start_offset = tr_start_offset.']));

    Simulink.BlockDiagram.arrangeSystem(modelName);
    save_system(modelName, modelPath);
    fprintf('Wrote %s\n', modelPath);
end

% --------------------------------------------------------------------------- %
function prepare_workspace()
    % Generate the drifted matched-filter stimulus into the base workspace.
    thisDir = fileparts(mfilename('fullpath'));
    matlabDir = fullfile(fileparts(thisDir), 'matlab');
    rtlDir = fullfile(fileparts(thisDir), 'rtl');

    bits = read_bits(fullfile(rtlDir, 'bpsk_frame_bits.mem'), 281);
    taps = read_taps(fullfile(rtlDir, 'bpsk_rrc_tx_fir_taps.mem'));

    syms = (bits * 2 - 1) * 0.82;
    up = zeros(1, numel(syms) * 8); up(1:8:end) = syms;
    tx = conv(up, taps);
    rx = resample_drift(tx, 8.03) * 0.07;
    mf = conv(rx, taps);
    mf_int = max(min(round(mf * 32768), 32767), -32768);

    t = (0:numel(mf_int)-1)';
    assignin('base', 'tr_mf_ts', timeseries(mf_int(:), t));
    assignin('base', 'tr_stop_time', numel(mf_int) - 1);
    assignin('base', 'tr_start_offset', 64);
    assignin('base', 'tr_expected_bits', bits(:));
    fprintf('prepared %d matched-filter samples (drift SPS=8.03), start_offset=64\n', numel(mf_int));

    % Also drop a tiny InitFcn helper so the model reloads stimulus on open.
    helper = fullfile(thisDir, 'bpsk_timing_recovery_build_simulink_workspace.m');
    if exist(helper, 'file') ~= 2
        fid = fopen(helper, 'w');
        fprintf(fid, '%% Auto-generated: rebuild the timing-recovery stimulus in the base workspace.\n');
        fprintf(fid, 'run(fullfile(fileparts(mfilename(''fullpath'')), ''bpsk_timing_recovery_build_simulink''));\n');
        fclose(fid);
    end
end

function code = timing_recovery_step_code()
    % HDL-Coder-friendly per-sample step (persistent state), bit-exact with the RTL.
    code = strjoin({
'function [out_sym, out_valid] = fcn(mf_in, in_valid)'
'%#codegen'
'    NCO_ONE = int32(65536); W_NOMINAL = int32(16384);'
'    K1 = int32(256); K2 = int32(16);'
'    W_MIN = int32(14336); W_MAX = int32(18432);'
'    START_OFFSET = int32(64); N_SYM = int32(281);'
'    persistent nco w integ x_prev y_on_prev y_mid parity started in_count emitted'
'    if isempty(nco)'
'        nco = int32(0); w = W_NOMINAL; integ = int32(0);'
'        x_prev = int32(0); y_on_prev = int32(0); y_mid = int32(0);'
'        parity = int32(0); started = false; in_count = int32(0); emitted = int32(0);'
'    end'
'    out_sym = int32(0); out_valid = false;'
'    cur = int32(mf_in);'
'    if in_valid'
'        if ~started'
'            if in_count == START_OFFSET'
'                started = true; nco = int32(0);'
'            else'
'                in_count = in_count + 1; x_prev = cur; return;'
'            end'
'        end'
'        if emitted < N_SYM'
'            if nco < w'
'                mu = min(nco * 4, int32(65535));'
'                y = x_prev + idivide(mu * (cur - x_prev), int32(65536), ''floor'');'
'                if parity == 0'
'                    e = int32(sign(double(y_mid)) * sign(double(y - y_on_prev)));'
'                    integ = integ + K2 * e;'
'                    wv = W_NOMINAL + K1 * e + integ;'
'                    w = max(W_MIN, min(W_MAX, wv));'
'                    y_on_prev = y;'
'                    out_sym = y; out_valid = true;'
'                    emitted = emitted + 1;'
'                else'
'                    y_mid = y;'
'                end'
'                parity = int32(1) - parity;'
'                nco = nco - w + NCO_ONE;'
'            else'
'                nco = nco - w;'
'            end'
'            x_prev = cur;'
'        end'
'    end'
'end'}, newline);
end

function set_matlab_function(blockPath, codeText)
    % Set the body of a MATLAB Function block via the Stateflow API.
    rt = sfroot;
    chart = rt.find('-isa', 'Stateflow.EMChart', 'Path', blockPath);
    chart.Script = codeText;
end

% --------------------------------------------------------------------------- %
function bits = read_bits(f, n)
    txt = strsplit(strtrim(fileread(f)));
    v = zeros(1, numel(txt));
    for k = 1:numel(txt), v(k) = bin2dec(txt{k}); end
    bits = v(1:n);
end

function taps = read_taps(f)
    txt = strsplit(strtrim(fileread(f)));
    t = zeros(1, numel(txt));
    for k = 1:numel(txt)
        x = hex2dec(txt{k});
        if x >= 32768, x = x - 65536; end
        t(k) = x;
    end
    taps = t / 32768;
end

function y = resample_drift(x, sps_actual)
    step = 8 / sps_actual;
    n = floor((numel(x) - 2) / step);
    t = (0:n-1) * step;
    i0 = floor(t);
    frac = t - i0;
    y = x(i0 + 1) .* (1 - frac) + x(i0 + 2) .* frac;
end
