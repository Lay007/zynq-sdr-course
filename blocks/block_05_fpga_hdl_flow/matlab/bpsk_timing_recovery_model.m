function bpsk_timing_recovery_model()
%BPSK_TIMING_RECOVERY_MODEL  Reference models for the Lab 5.8b Gardner symbol
%   timing-recovery loop (MATLAB mirror of bpsk_timing_recovery_model.py and the
%   HDL bpsk_symbol_timing_recovery.v).
%
%   Two interchangeable models of the same loop:
%     timing_recovery_float - readable floating-point reference,
%     timing_recovery_fixed - bit-exact integer model (the HDL spec).
%
%   Both use a decrementing modulo-1 NCO (2 strobes/symbol), a linear interpolator
%   (mu ~= nco<<2 for the nominal step w = 2/SPS), a sign-Gardner timing-error
%   detector e = sgn(y_mid)*sgn(y_on[k]-y_on[k-1]) (amplitude-independent) and a PI
%   loop filter with power-of-two gains (k1 = 1/256, k2 = 1/4096).
%
%   Running the function prints a float / fixed-point / fixed-phase BER comparison
%   on a time-drifted burst (SPS ~= 8): both timing-recovery models reach BER 0
%   while the Lab 5.8 fixed-phase decimator cannot follow the drift.

    bits = load_frame_bits(281);
    taps = load_rrc_taps();
    tx = tx_waveform(bits, taps, 0.82);

    fprintf('BPSK Gardner timing-recovery models (float / fixed-point / fixed-phase)\n');
    fprintf('drift | float TR | fixed-pt TR | fixed-phase (Lab 5.8)\n');
    for sps = [8.00 8.03 8.05 8.08 7.95 7.92]
        rx = resample_drift(tx, sps) * 0.07;            % 7%% full scale, like the radio
        mf = conv(rx, taps);
        mf_int = max(min(round(mf * 32768), 32767), -32768);
        bf = 999; bx = 999; bp = 999;
        for so = 40:129
            bf = min(bf, ber(timing_recovery_float(mf,     so, 281), bits));
            bx = min(bx, ber(timing_recovery_fixed(mf_int, so, 281), bits));
            bp = min(bp, ber(fixed_phase_decimate(mf_int,  so, 281), bits));
        end
        fprintf(' %5.2f | %8d | %11d | %d\n', sps, bf, bx, bp);
    end
end

% --------------------------------------------------------------------------- %
function bits = load_frame_bits(n)
    f = fullfile(rtl_dir(), 'bpsk_frame_bits.mem');
    txt = strsplit(strtrim(fileread(f)));
    v = zeros(1, numel(txt));
    for k = 1:numel(txt)
        v(k) = bin2dec(txt{k});       % frame bits are 0/1
    end
    bits = v(1:n);
end

function taps = load_rrc_taps()
    f = fullfile(rtl_dir(), 'bpsk_rrc_tx_fir_taps.mem');
    txt = strsplit(strtrim(fileread(f)));
    t = zeros(1, numel(txt));
    for k = 1:numel(txt)
        x = hex2dec(txt{k});
        if x >= 32768, x = x - 65536; end
        t(k) = x;
    end
    taps = t / 32768;
end

function d = rtl_dir()
    d = fullfile(fileparts(fileparts(mfilename('fullpath'))), 'rtl');
end

function w = tx_waveform(bits, taps, amp)
    syms = (bits * 2 - 1) * amp;        % 0 -> -1, 1 -> +1
    up = zeros(1, numel(syms) * 8);
    up(1:8:end) = syms;
    w = conv(up, taps);
end

function y = resample_drift(x, sps_actual)
    step = 8 / sps_actual;
    n = floor((numel(x) - 2) / step);
    t = (0:n-1) * step;
    i0 = floor(t);                      % 0-based positions
    frac = t - i0;
    y = x(i0 + 1) .* (1 - frac) + x(i0 + 2) .* frac;
end

function s = sgn(x)
    s = (x > 0) - (x < 0);
end

function e = ber(rec, bits)
    n = min(numel(rec), numel(bits));
    rec = rec(1:n); b = bits(1:n);
    e = min(sum(rec ~= b), sum((1 - rec) ~= b));
end

% --------------------------------------------------------------------------- %
function bits_out = timing_recovery_float(mf, start_offset, n_sym)
    k1 = 1/256; k2 = 1/4096;
    nco = 0; w = 0.25; integ = 0;
    x_prev = 0; y_on_prev = 0; y_mid = 0;
    parity = 0; started = false; in_count = 0; emitted = 0;
    bits_out = zeros(1, n_sym); got = 0;
    for idx = 1:numel(mf)
        cur = mf(idx);
        if ~started
            if in_count == start_offset
                started = true; nco = 0;
            else
                in_count = in_count + 1; x_prev = cur; continue;
            end
        end
        if nco < w
            mu = min(nco / w, 0.999985);
            y = x_prev + mu * (cur - x_prev);
            if parity == 0
                e = sgn(y_mid) * sgn(y - y_on_prev);
                integ = integ + k2 * e;
                w = min(max(0.25 + k1 * e + integ, 0.20), 0.30);
                y_on_prev = y;
                got = got + 1; bits_out(got) = (y < 0);
                emitted = emitted + 1;
                if emitted >= n_sym, break; end
            else
                y_mid = y;
            end
            parity = 1 - parity;
            nco = nco - w + 1.0;
        else
            nco = nco - w;
        end
        x_prev = cur;
    end
    bits_out = bits_out(1:got);
end

% --------------------------------------------------------------------------- %
function bits_out = timing_recovery_fixed(mf_int, start_offset, n_sym)
    NCO_ONE = 65536; W_NOMINAL = 16384; K1 = 256; K2 = 16;
    W_MIN = W_NOMINAL - 2048; W_MAX = W_NOMINAL + 2048;
    nco = 0; w = W_NOMINAL; integ = 0;
    x_prev = 0; y_on_prev = 0; y_mid = 0;
    parity = 0; started = false; in_count = 0; emitted = 0;
    bits_out = zeros(1, n_sym); got = 0;
    for idx = 1:numel(mf_int)
        cur = mf_int(idx);
        if ~started
            if in_count == start_offset
                started = true; nco = 0;
            else
                in_count = in_count + 1; x_prev = cur; continue;
            end
        end
        if nco < w
            mu = min(nco * 4, 65535);                       % nco<<2
            y = x_prev + floor((mu * (cur - x_prev)) / 65536);  % arithmetic >>16
            if parity == 0
                e = sgn(y_mid) * sgn(y - y_on_prev);
                integ = integ + K2 * e;
                w = max(W_MIN, min(W_MAX, W_NOMINAL + K1 * e + integ));
                y_on_prev = y;
                got = got + 1; bits_out(got) = (y < 0);
                emitted = emitted + 1;
                if emitted >= n_sym, break; end
            else
                y_mid = y;
            end
            parity = 1 - parity;
            nco = nco - w + NCO_ONE;
        else
            nco = nco - w;
        end
        x_prev = cur;
    end
    bits_out = bits_out(1:got);
end

% --------------------------------------------------------------------------- %
function bits_out = fixed_phase_decimate(mf, start_offset, n_sym)
    % Lab 5.8 fixed-phase decimator (no timing recovery), for comparison.
    idx = start_offset + (0:n_sym-1) * 8 + 1;     % 1-based
    idx = idx(idx <= numel(mf));
    bits_out = double(mf(idx) < 0);
end
