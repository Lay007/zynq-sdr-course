/*
 * zofdm - issue #48 stage 4b: OFDM frames through the radio with the fabric modem of the OFDM image
 * (ofdm_radio_core at 0x79060000, COURSE_OVERLAY_MODE=ofdm_txrx). The fabric does the preamble,
 * the modem, the frame search and the decisions; this program writes bits, starts, and reads back.
 *
 *   one board, TX1 cabled to RX1 through at least 30 dB:
 *     board$ ./zofdm loop --frames 100 --symbols 10
 *   two boards (B listens first, then A transmits):
 *     board-b$ ./zofdm rx --frames 100 --symbols 10 --timeout 120
 *     board-a$ ./zofdm tx --frames 100 --symbols 10 --period-ms 50
 *   board$ ./zofdm regs          the core's and the modem's registers
 *   board$ ./zofdm stop          TX gain to minimum, TX LO off, zero stream stopped
 *
 * Frame content: word 0 of the data is the frame number, the other words come from a xorshift32
 * seeded by it, so the receiver regenerates what was sent from what it received and counts bit
 * errors without any side channel; a frame whose word 0 is not a plausible number counts as lost.
 * Options: --rate (default 2083334, at most 6.25 MS/s for the core), --lo, --tx-gain (dB, AD9361),
 * --rx-gain (dB, manual), --core-gain (Q4.12 digital gain, default 9170 = +7 dB), --rx-shift
 * (0..8, default 4: the AD9361's 12 bits to Q1.15), --config (core 2.x: 1 = coarse CFO from the
 * preamble, 2 = level normalization, default 3 = both; with the level stage --rx-shift stays 4).
 * The CFO printed is the preamble's coarse estimate plus the modem's residual.
 *
 * Build: arm-linux-gnueabihf-gcc -O2 -static -o zofdm zofdm.c
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <fcntl.h>
#include <math.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define OFDM_BASE 0x79060000u
#define DAC_BASE 0x79024000u

/* ofdm_radio_core registers */
#define R_ID 0x000
#define R_CONTROL 0x008
#define R_STATUS 0x00C
#define R_DATA_SYMBOLS 0x010
#define R_TX_GAIN 0x014
#define R_RX_SHIFT 0x018
#define R_MAX_SYMBOLS 0x01C
#define R_FRAMES_FOUND 0x020
#define R_FRAMES_MISSED 0x024
#define R_SYNC_OVERFLOWS 0x028
#define R_RX_SYMBOLS 0x02C
#define R_TX_SAMPLES 0x030
#define R_TX_UNDERFLOWS 0x034
#define R_RX_OVERFLOWS 0x038
#define R_RX_SAMPLES 0x03C
#define R_VERSION 0x004
#define R_CONFIG 0x040              /* core 2.x: [0] coarse CFO, [1] level */
#define R_THETA 0x044
#define R_GAIN_K 0x048
#define R_MODEM 0x100
#define R_TXBUF 0x400
#define R_RXBUF 0x800
/* the modem's own registers, through the core's window */
#define M_STATUS (R_MODEM + 0x0C)
#define M_RX_SYMBOLS (R_MODEM + 0x20)
#define M_CE_TRAINED (R_MODEM + 0x30)
#define M_CFO_THETA (R_MODEM + 0x34)

#define ST_TX_BUSY (1u << 0)
#define ST_TX_DONE (1u << 1)
#define ST_RX_FOUND (1u << 3)
#define ST_RX_DONE (1u << 4)

static volatile uint32_t *core, *dac;
static char phy[128];
static long rate = 2083334, lo = 915000000;
static double tx_gain = -10.0;
static int rx_gain = 71, core_gain = 9170, rx_shift = 4, symbols = 4, frames = 10, config = 3;
static uint32_t core_version;
static double timeout_s = 10.0, period_ms = 20.0;

static uint32_t rd(uint32_t off) { return core[off / 4]; }
static void wr(uint32_t off, uint32_t v) { core[off / 4] = v; }

static double now_s(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static int find_phy(void)
{
    char p[256], name[64];
    for (int i = 0; i < 8; i++) {
        snprintf(p, sizeof p, "/sys/bus/iio/devices/iio:device%d/name", i);
        FILE *f = fopen(p, "r");
        if (!f)
            continue;
        if (fgets(name, sizeof name, f) && strncmp(name, "ad9361-phy", 10) == 0) {
            snprintf(phy, sizeof phy, "/sys/bus/iio/devices/iio:device%d", i);
            fclose(f);
            return 0;
        }
        fclose(f);
    }
    return -1;
}

/* Written only when the value differs (a rewrite retunes the chip, as in zmbox). */
static void attr(const char *name, const char *value)
{
    char p[256], cur[64];
    snprintf(p, sizeof p, "%s/%s", phy, name);
    FILE *f = fopen(p, "r");
    if (f) {
        int same = 0;
        if (fgets(cur, sizeof cur, f)) {
            char *end;
            double a = strtod(cur, &end), b;
            cur[strcspn(cur, "\n")] = 0;
            same = !strcmp(cur, value) || (end != cur && sscanf(value, "%lf", &b) == 1 && fabs(a - b) <= 0.01);
        }
        fclose(f);
        if (same)
            return;
    }
    f = fopen(p, "w");
    if (!f) {
        fprintf(stderr, "cannot write %s\n", p);
        return;
    }
    fputs(value, f);
    fclose(f);
}

static int writers_running(int kill_them)
{
    DIR *d = opendir("/proc");
    struct dirent *e;
    char p[300], comm[64];
    int n = 0;
    while (d && (e = readdir(d))) {
        int pid = atoi(e->d_name);
        if (pid <= 0)
            continue;
        snprintf(p, sizeof p, "/proc/%d/comm", pid);
        FILE *f = fopen(p, "r");
        if (!f)
            continue;
        if (fgets(comm, sizeof comm, f) && strncmp(comm, "iio_writedev", 12) == 0) {
            n++;
            if (kill_them)
                kill(pid, 15);
        }
        fclose(f);
    }
    if (d)
        closedir(d);
    return n;
}

static volatile uint32_t *map(int fd, uint32_t base)
{
    void *m = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE, MAP_SHARED, fd, base);
    return m == MAP_FAILED ? NULL : (volatile uint32_t *)m;
}

static int open_regs(void)
{
    int fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) {
        perror("/dev/mem");
        return -1;
    }
    core = map(fd, OFDM_BASE);
    dac = map(fd, DAC_BASE);
    if (!core || !dac) {
        perror("mmap");
        return -1;
    }
    if (rd(R_ID) != 0x4F464452u) {
        fprintf(stderr, "no ofdm_radio_core at 0x%08x (id 0x%08x): is the OFDM image loaded?\n", OFDM_BASE, rd(R_ID));
        return -1;
    }
    core_version = rd(R_VERSION);
    return 0;
}

static void radio_setup(int transmit)
{
    char v[64];
    snprintf(v, sizeof v, "%ld", rate);
    attr("in_voltage_sampling_frequency", v);
    snprintf(v, sizeof v, "%ld", lo);
    attr("out_altvoltage0_RX_LO_frequency", v);
    attr("out_altvoltage1_TX_LO_frequency", v);
    attr("in_voltage0_gain_control_mode", "manual");
    snprintf(v, sizeof v, "%d", rx_gain);
    attr("in_voltage0_hardwaregain", v);
    if (transmit) {
        /* zeros between bursts: the mux writes them by itself (#67); the stream is belt and braces */
        if (!getenv("ZOFDM_NO_ZERO_STREAM") && !writers_running(0)) {
            int16_t zero[2 * 1024] = {0};
            FILE *f = fopen("/tmp/zofdm_zero.bin", "wb");
            if (f) {
                fwrite(zero, sizeof zero, 1, f);
                fclose(f);
            }
            if (system("nohup iio_writedev -c -b 1024 -s 1024 cf-ad9361-dds-core-lpc voltage0 voltage1 "
                       "< /tmp/zofdm_zero.bin > /dev/null 2>&1 &") != 0)
                fprintf(stderr, "could not start the zero stream\n");
            usleep(500000);
        }
        /* TX1 (I0, Q0) to the DMA input, where the mux puts the burst; TX2 to zero (see zmbox) */
        for (int c = 0; c < 4; c++)
            dac[(0x418 + 0x40 * c) / 4] = c < 2 ? 2 : 3;
        dac[0x044 / 4] = 1;
        snprintf(v, sizeof v, "%.2f", tx_gain);
        attr("out_voltage0_hardwaregain", v);
        attr("out_altvoltage1_TX_LO_powerdown", "0");
    }
    wr(R_DATA_SYMBOLS, (uint32_t)symbols);
    wr(R_TX_GAIN, (uint32_t)core_gain);
    wr(R_RX_SHIFT, (uint32_t)rx_shift);
    if (core_version >= 0x00020000u)
        wr(R_CONFIG, (uint32_t)config);
    symbols = (int)rd(R_DATA_SYMBOLS);
}

static uint32_t xs32(uint32_t *s)
{
    uint32_t x = *s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return *s = x;
}

static void frame_words(uint32_t number, uint32_t *w, int n)
{
    uint32_t s = number * 0x9E3779B9u + 0x2545F491u;
    w[0] = number;
    for (int k = 1; k < n; k++)
        w[k] = xs32(&s);
}

static int popcount32(uint32_t v)
{
    int c = 0;
    while (v) {
        v &= v - 1;
        c++;
    }
    return c;
}

/* The carrier offset of the last frame: the preamble's coarse estimate (core 2.x, THETA, 2^16 = one
 * turn over 32 samples) plus what the modem's CP correlation found after that correction. */
static double coarse_cfo_hz(void)
{
    if (core_version < 0x00020000u)
        return 0.0;
    int32_t theta = (int32_t)rd(R_THETA);
    return (double)theta / 2097152.0 * (double)rate;
}

static double cfo_hz(void)
{
    int32_t theta = (int32_t)rd(M_CFO_THETA);
    return coarse_cfo_hz() - (double)theta / 16777216.0 / 64.0 * (double)rate;
}

static int gain_k(void)
{
    return core_version < 0x00020000u ? 0 : (int)(int32_t)rd(R_GAIN_K);
}

static void put_frame(uint32_t number)
{
    uint32_t w[256];
    int n = 3 * symbols;
    frame_words(number, w, n);
    for (int k = 0; k < n; k++)
        wr(R_TXBUF + 4 * k, w[k]);
}

static int wait_status(uint32_t mask, double seconds)
{
    double t0 = now_s();
    while (now_s() - t0 < seconds) {
        if (rd(R_STATUS) & mask)
            return 1;
        usleep(200);
    }
    return 0;
}

/* Received frame: bit errors against the frame its word 0 names; -1 when word 0 is implausible. */
static int check_frame(uint32_t max_number, uint32_t *number)
{
    uint32_t got[256], want[256];
    int n = 3 * symbols, errors = 0;
    for (int k = 0; k < n; k++)
        got[k] = rd(R_RXBUF + 4 * k);
    *number = got[0];
    if (got[0] >= max_number)
        return -1;
    frame_words(got[0], want, n);
    for (int k = 1; k < n; k++)
        errors += popcount32(got[k] ^ want[k]);
    return errors;
}

static void regs(void)
{
    static const struct { uint32_t off; const char *name; } r[] = {
        {R_STATUS, "STATUS"}, {R_DATA_SYMBOLS, "DATA_SYMBOLS"}, {R_TX_GAIN, "TX_GAIN"},
        {R_RX_SHIFT, "RX_SHIFT"}, {R_MAX_SYMBOLS, "MAX_SYMBOLS"}, {R_FRAMES_FOUND, "FRAMES_FOUND"},
        {R_FRAMES_MISSED, "FRAMES_MISSED"}, {R_SYNC_OVERFLOWS, "SYNC_OVERFLOWS"},
        {R_RX_SYMBOLS, "RX_SYMBOLS"}, {R_TX_SAMPLES, "TX_SAMPLES"}, {R_TX_UNDERFLOWS, "TX_UNDERFLOWS"},
        {R_RX_OVERFLOWS, "RX_OVERFLOWS"}, {R_RX_SAMPLES, "RX_SAMPLES"}, {M_STATUS, "MODEM_STATUS"},
        {M_RX_SYMBOLS, "MODEM_RX_SYMBOLS"}, {M_CE_TRAINED, "MODEM_CE_TRAINED"}, {M_CFO_THETA, "MODEM_CFO_THETA"},
        {R_VERSION, "VERSION"}, {R_CONFIG, "CONFIG"}, {R_THETA, "PREAMBLE_THETA"}, {R_GAIN_K, "GAIN_K"},
    };
    for (unsigned k = 0; k < sizeof r / sizeof r[0]; k++)
        printf("%-18s 0x%08x %u\n", r[k].name, rd(r[k].off), rd(r[k].off));
    printf("CFO estimate       %.0f Hz (preamble %.0f Hz, at %ld S/s), gain 2^(%d/2)\n", cfo_hz(), coarse_cfo_hz(),
           rate, gain_k());
}

static int loop(void)
{
    long bits = 0, errors = 0;
    int lost = 0;
    radio_setup(1);
    for (int f = 0; f < frames; f++) {
        uint32_t number;
        put_frame((uint32_t)f);
        wr(R_CONTROL, 0x101);                                  /* RX_ARM, clear sticky flags */
        wr(R_CONTROL, 0x2);                                    /* TX_START */
        int done = wait_status(ST_RX_DONE, 0.5);
        wait_status(ST_TX_DONE, 0.5);
        int e = done ? check_frame((uint32_t)frames, &number) : -1;
        if (e < 0 || number != (uint32_t)f) {
            lost++;
            printf("frame %d: lost (found %u, rx symbols %u, status 0x%x)\n", f, rd(R_FRAMES_FOUND),
                   rd(R_RX_SYMBOLS), rd(R_STATUS));
        } else {
            bits += 96L * symbols - 32;
            errors += e;
            printf("frame %d: %d bit errors, CFO %.0f Hz (preamble %.0f), gain 2^(%d/2), found %u\n", f, e,
                   cfo_hz(), coarse_cfo_hz(), gain_k(), rd(R_FRAMES_FOUND));
        }
        usleep((useconds_t)(period_ms * 1000));
    }
    printf("RESULT frames=%d lost=%d bits=%ld bit_errors=%ld symbols=%d rate=%ld lo=%ld tx_gain=%.2f rx_gain=%d\n",
           frames, lost, bits, errors, symbols, rate, lo, tx_gain, rx_gain);
    return 0;
}

static int tx(void)
{
    radio_setup(1);
    for (int f = 0; f < frames; f++) {
        put_frame((uint32_t)f);
        wr(R_CONTROL, 0x2);
        if (!wait_status(ST_TX_DONE, 0.5))
            fprintf(stderr, "frame %d: TX did not finish (status 0x%x)\n", f, rd(R_STATUS));
        usleep((useconds_t)(period_ms * 1000));
    }
    printf("TX frames=%d symbols=%d underflows=%u\n", frames, symbols, rd(R_TX_UNDERFLOWS));
    return 0;
}

static int rx(void)
{
    long bits = 0, errors = 0;
    int received = 0, garbled = 0;
    double t0 = now_s();
    radio_setup(0);
    wr(R_CONTROL, 0x101);
    while (received + garbled < frames && now_s() - t0 < timeout_s) {
        if (!(rd(R_STATUS) & ST_RX_DONE)) {
            usleep(200);
            continue;
        }
        uint32_t number;
        int e = check_frame((uint32_t)frames, &number);
        double cfo = cfo_hz(), coarse = coarse_cfo_hz();        /* RX_ARM clears them: read first */
        int k = gain_k();
        wr(R_CONTROL, 0x101);                                  /* re-arm at once */
        if (e < 0) {
            garbled++;
            printf("frame ?: word 0 = 0x%08x, not a frame number\n", number);
        } else {
            received++;
            bits += 96L * symbols - 32;
            errors += e;
            printf("frame %u: %d bit errors, CFO %.0f Hz (preamble %.0f), gain 2^(%d/2)\n", number, e, cfo, coarse, k);
        }
    }
    printf("RESULT expected=%d received=%d garbled=%d bits=%ld bit_errors=%ld symbols=%d rate=%ld lo=%ld rx_gain=%d\n",
           frames, received, garbled, bits, errors, symbols, rate, lo, rx_gain);
    return 0;
}

static void stop(void)
{
    writers_running(1);
    attr("out_voltage0_hardwaregain", "-89.75");
    attr("out_altvoltage1_TX_LO_powerdown", "1");
    wr(R_CONTROL, 0x4);
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: zofdm loop|tx|rx|regs|stop [options], see the source header\n");
        return 2;
    }
    for (int i = 2; i + 1 < argc; i += 2) {
        const char *o = argv[i], *v = argv[i + 1];
        if (!strcmp(o, "--frames")) frames = atoi(v);
        else if (!strcmp(o, "--symbols")) symbols = atoi(v);
        else if (!strcmp(o, "--rate")) rate = atol(v);
        else if (!strcmp(o, "--lo")) lo = atol(v);
        else if (!strcmp(o, "--tx-gain")) tx_gain = atof(v);
        else if (!strcmp(o, "--rx-gain")) rx_gain = atoi(v);
        else if (!strcmp(o, "--core-gain")) core_gain = atoi(v);
        else if (!strcmp(o, "--rx-shift")) rx_shift = atoi(v);
        else if (!strcmp(o, "--config")) config = atoi(v);
        else if (!strcmp(o, "--timeout")) timeout_s = atof(v);
        else if (!strcmp(o, "--period-ms")) period_ms = atof(v);
        else {
            fprintf(stderr, "unknown option %s\n", o);
            return 2;
        }
    }
    if (rate > 6250000) {
        fprintf(stderr, "--rate %ld: the core takes at most one sample every 16 clocks (6.25 MS/s)\n", rate);
        return 2;
    }
    if (find_phy() || open_regs())
        return 1;
    if (!strcmp(argv[1], "loop")) return loop();
    if (!strcmp(argv[1], "tx")) return tx();
    if (!strcmp(argv[1], "rx")) return rx();
    if (!strcmp(argv[1], "regs")) { regs(); return 0; }
    if (!strcmp(argv[1], "stop")) { stop(); return 0; }
    fprintf(stderr, "unknown command %s\n", argv[1]);
    return 2;
}
