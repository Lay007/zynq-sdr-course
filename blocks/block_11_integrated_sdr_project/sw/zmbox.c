/*
 * zmbox - Lab 11.49: send a text message through the PS/PL mailbox and the fabric QPSK modem on one
 * board (board B, TX1 cabled to RX1 through at least 30 dB), and read what came back.
 *
 *   board-b$ ./zmbox send "Hello from the mailbox" --seq 17
 *   TX sequence=17 bytes=22 payload="Hello from the mailbox"
 *   RX sequence=17 bytes=22 meta=CRC_OK payload="Hello from the mailbox"
 *   board-b$ ./zmbox stop
 *
 * or receive a message that another board sends once (board A: zmsg send --once, Lab 11.48):
 *
 *   board-b$ ./zmbox listen --timeout 60
 *   RX sequence=17 bytes=18 meta=CRC_OK payload="Hello from board A"
 *
 * or chat between two boards that both run the mailbox image (Lab 11.50): every line typed is
 * sent, everything received is printed:
 *
 *   board-a$ ./zmbox chat --name A        board-b$ ./zmbox chat --name B
 *
 * The program uses only the Lab 5.12 register contract: TX_SEQUENCE, TX_LENGTH, TX_DATA, TX_START,
 * then STATUS.RX_VALID, RX_SEQUENCE, RX_LENGTH, RX_META, RX_DATA, RX_ACK. Packet-v1 framing, CRC,
 * whitening, the burst and the reception all happen in the fabric (mailbox MODE = 1 inside the
 * bridge wrapper at 0x79050000). Before that it sets up the radio the way Lab 11.47 does: the DAC
 * channels to the DMA input, a cyclic iio_writedev buffer of zeros so the DAC FIFO is fed between
 * bursts, LOs and gains, and the modem mode words in the gpreg block at 0x79040000.
 *
 * Build: arm-linux-gnueabihf-gcc -O2 -static -o zmbox zmbox.c
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <math.h>
#include <poll.h>
#include <unistd.h>

#define GP_BASE 0x79040000u
#define MB_BASE 0x79050000u
#define DAC_BASE 0x79024000u
#define MODE 0x2D630u           /* Lab 11.45: QPSK, raw ADC, DC blocker, Costas, phase pick, Gardner, diff */
#define FS 3840000

/* Lab 5.12 mailbox registers */
#define MB_ID 0x00
#define MB_VERSION 0x04
#define MB_CONTROL 0x08
#define MB_STATUS 0x0C
#define MB_TX_SEQUENCE 0x10
#define MB_TX_LENGTH 0x14
#define MB_TX_DATA0 0x20
#define MB_RX_SEQUENCE 0x60
#define MB_RX_LENGTH 0x64
#define MB_RX_META 0x68
#define MB_RX_DATA0 0x70

static char phy[128];
static volatile uint32_t *gp, *mb, *dac;

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

/* Written only when the value differs: rewriting the LO or the sample rate retunes the chip even
 * when nothing changes, and the TX calibration that follows puts tens of milliseconds of a strong
 * signal on the air right before the burst (as in zmsg, Lab 11.48). */
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

static int zero_stream_running(void)
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
        if (fgets(comm, sizeof comm, f) && strncmp(comm, "iio_writedev", 12) == 0)
            n++;
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

static uint32_t mbr(uint32_t off) { return mb[off / 4]; }
static void mbw(uint32_t off, uint32_t v) { mb[off / 4] = v; }
static void gpw(uint32_t off, uint32_t v) { gp[(0x400 + off) / 4] = v; }

static int open_regs(void)
{
    int fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) {
        perror("/dev/mem");
        return -1;
    }
    gp = map(fd, GP_BASE);
    mb = map(fd, MB_BASE);
    dac = map(fd, DAC_BASE);
    if (!gp || !mb || !dac) {
        perror("mmap");
        return -1;
    }
    if (gp[0x508 / 4] != 0x4250534Bu) {
        fprintf(stderr, "no course modem at 0x%08x\n", GP_BASE);
        return -1;
    }
    if (mbr(MB_ID) != 0x4D424F58u || mbr(MB_VERSION) != 0x00020000u) {
        fprintf(stderr, "no message mailbox (MODE 1) at 0x%08x: id 0x%08x version 0x%08x\n", MB_BASE,
                mbr(MB_ID), mbr(MB_VERSION));
        return -1;
    }
    return 0;
}

static void radio_setup(double tx_gain, int rx_gain, long lo, int offset)
{
    char v[64];
    snprintf(v, sizeof v, "%d", FS);
    attr("in_voltage_sampling_frequency", v);
    snprintf(v, sizeof v, "%ld", lo);
    attr("out_altvoltage0_RX_LO_frequency", v);
    attr("out_altvoltage1_TX_LO_frequency", v);
    attr("in_voltage0_gain_control_mode", "manual");
    snprintf(v, sizeof v, "%d", rx_gain);
    attr("in_voltage0_hardwaregain", v);
    /* Keep the DAC FIFO fed with zeros between bursts (Lab 11.47). Images with the #67 fix write
     * zeros into the FIFO by themselves; ZMBOX_NO_ZERO_STREAM=1 skips the stream to check that. */
    if (!getenv("ZMBOX_NO_ZERO_STREAM") && !zero_stream_running()) {
        int16_t zero[2 * 1024] = {0};
        FILE *f = fopen("/tmp/zmbox_zero.bin", "wb");
        if (f) {
            fwrite(zero, sizeof zero, 1, f);
            fclose(f);
        }
        if (system("nohup iio_writedev -c -b 1024 -s 1024 cf-ad9361-dds-core-lpc voltage0 voltage1 "
                   "< /tmp/zmbox_zero.bin > /dev/null 2>&1 &") != 0)
            fprintf(stderr, "could not start the zero stream\n");
        usleep(500000);
    }
    /* TX1 (I0, Q0) to the DMA input, where the bridge muxes the burst in; TX2 to zero. Only two
     * channels: the DAC core enables a channel in the unpacker exactly when its source is DMA, so
     * with all four on DMA a later two-channel buffer (zmsg) is unpacked as four channels and TX1
     * plays every second sample, twice as fast. */
    for (int c = 0; c < 4; c++)
        dac[(0x418 + 0x40 * c) / 4] = c < 2 ? 2 : 3;
    dac[0x044 / 4] = 1;
    snprintf(v, sizeof v, "%.2f", tx_gain);
    attr("out_voltage0_hardwaregain", v);
    attr("out_altvoltage1_TX_LO_powerdown", "0");
    /* Modem mode words: the Lab 11.45 frame (152 symbols, 48-bit preamble). */
    gpw(0x44, 152);
    gpw(0x84, 48);
    gpw(0xC4, (uint32_t)offset);
    gpw(0x04, MODE);
}

static int send(const char *text, int seq, int quiet)
{
    int len = (int)strlen(text);
    if (len > 27)
        fprintf(stderr, "payload is %d bytes; the mailbox modem sends at most 27 (expect FRAME_ERROR)\n", len);
    uint8_t buf[64] = {0};
    memcpy(buf, text, len > 64 ? 64 : len);
    mbw(MB_CONTROL, 2);                       /* drop an old unread message */
    mbw(MB_TX_SEQUENCE, (uint32_t)seq);
    mbw(MB_TX_LENGTH, (uint32_t)len);
    for (int w = 0; w < 16; w++)
        mbw(MB_TX_DATA0 + 4 * w, buf[4 * w] | (buf[4 * w + 1] << 8) | (buf[4 * w + 2] << 16) | ((uint32_t)buf[4 * w + 3] << 24));
    if (!quiet)
        printf("TX sequence=%d bytes=%d payload=\"%s\"\n", seq, len, text);
    mbw(MB_CONTROL, 1);                       /* TX_START */
    double t_end = now_s() + 1.0;
    uint32_t st = 0;
    while (now_s() < t_end && !((st = mbr(MB_STATUS)) & 0x4))
        usleep(100);
    if (!(st & 0x4)) {
        printf("RX nothing (status 0x%x)\n", st);
        return 1;
    }
    uint32_t meta = mbr(MB_RX_META), rlen = mbr(MB_RX_LENGTH), rseq = mbr(MB_RX_SEQUENCE);
    char out[65] = {0};
    for (int w = 0; w < 7; w++) {
        uint32_t d = mbr(MB_RX_DATA0 + 4 * w);
        for (int b = 0; b < 4; b++)
            out[4 * w + b] = (char)((d >> (8 * b)) & 0xFF);
    }
    mbw(MB_CONTROL, 2);                       /* RX_ACK */
    const char *m = (meta & 1) ? "CRC_OK" : (meta & 2) ? "FRAME_ERROR" : "CRC_BAD";
    printf("RX sequence=%u bytes=%u meta=%s payload=\"%.*s\"\n", rseq, rlen, m, (int)(rlen <= 27 ? rlen : 0), out);
    fflush(stdout);
    return (meta & 1) && rseq == (uint32_t)(seq & 0xFFFF) && rlen == (uint32_t)len && !memcmp(out, text, len) ? 0 : 1;
}

static volatile sig_atomic_t stop_requested;
static void on_term(int sig) { (void)sig; stop_requested = 1; }

/* CONTROL.RX_LISTEN: the mailbox keeps listening (listen mode of issue #68) and delivers every
 * frame whose CRC matches; print each one, acknowledge it, until count or timeout. */
static int listen_loop(int count, double timeout, int rx_gain, long lo)
{
    char v[64];
    snprintf(v, sizeof v, "%d", FS);
    attr("in_voltage_sampling_frequency", v);
    snprintf(v, sizeof v, "%ld", lo);
    attr("out_altvoltage0_RX_LO_frequency", v);
    attr("in_voltage0_gain_control_mode", "manual");
    snprintf(v, sizeof v, "%d", rx_gain);
    attr("in_voltage0_hardwaregain", v);
    gpw(0x44, 152);
    gpw(0x84, 48);
    gpw(0xC4, 0);
    gpw(0x04, MODE);
    signal(SIGTERM, on_term);
    signal(SIGINT, on_term);
    mbw(MB_CONTROL, 2);                       /* RX_ACK: start empty */
    mbw(MB_CONTROL, 4);                       /* RX_LISTEN */
    int got = 0, overflows = 0;
    double t_end = now_s() + timeout;
    while (!stop_requested && got < count && now_s() < t_end) {
        uint32_t st = mbr(MB_STATUS);
        if (!(st & 0x4)) {
            usleep(1000);
            continue;
        }
        overflows += (st & 0x8) != 0;
        uint32_t meta = mbr(MB_RX_META), rlen = mbr(MB_RX_LENGTH), rseq = mbr(MB_RX_SEQUENCE);
        char out[29] = {0};
        for (int w = 0; w < 7; w++) {
            uint32_t d = mbr(MB_RX_DATA0 + 4 * w);
            for (int b = 0; b < 4; b++)
                out[4 * w + b] = (char)((d >> (8 * b)) & 0xFF);
        }
        mbw(MB_CONTROL, 2);                   /* RX_ACK */
        got++;
        printf("RX sequence=%u bytes=%u meta=%s payload=\"%.*s\"\n", rseq, rlen, (meta & 1) ? "CRC_OK" : "?",
               (int)(rlen <= 27 ? rlen : 0), out);
        fflush(stdout);
    }
    mbw(MB_CONTROL, 8);                       /* RX_STOP */
    fprintf(stderr, "listened %.1f s, delivered %d, overflows seen %d\n", timeout - (t_end - now_s()), got, overflows);
    return got ? 0 : 1;
}

/* Read the RX registers into text and acknowledge; returns the RX length. */
static uint32_t take_rx(uint32_t *seq, uint32_t *meta, char *out)
{
    *meta = mbr(MB_RX_META);
    uint32_t rlen = mbr(MB_RX_LENGTH);
    *seq = mbr(MB_RX_SEQUENCE);
    for (int w = 0; w < 7; w++) {
        uint32_t d = mbr(MB_RX_DATA0 + 4 * w);
        for (int b = 0; b < 4; b++)
            out[4 * w + b] = (char)((d >> (8 * b)) & 0xFF);
    }
    out[rlen <= 27 ? rlen : 0] = 0;
    mbw(MB_CONTROL, 2);                       /* RX_ACK */
    return rlen;
}

/* Chat: listen all the time; a typed line stops listening, goes out with TX_START (the board
 * also hears its own burst in that attempt, which is discarded), then listening resumes. */
static int chat(const char *name, double tx_gain, int rx_gain, long lo)
{
    radio_setup(tx_gain, rx_gain, lo, 1);
    signal(SIGTERM, on_term);
    signal(SIGINT, on_term);
    mbw(MB_CONTROL, 2);
    mbw(MB_CONTROL, 4);                       /* RX_LISTEN */
    printf("chat as %s: type a line (at most 27 bytes with the name) and press Enter; Ctrl-C ends\n", name);
    fflush(stdout);
    int seq = 1;
    char line[128], out[29];
    struct pollfd pfd = {.fd = 0, .events = POLLIN};
    while (!stop_requested) {
        uint32_t st = mbr(MB_STATUS), rseq, meta;
        if (st & 0x4) {
            take_rx(&rseq, &meta, out);
            if (meta & 1) {
                printf("<< %s\n", out);
                fflush(stdout);
            } else if (getenv("ZMBOX_DEBUG")) {
                printf("-- packet dropped, meta 0x%x seq %u at %.3f s\n", meta, rseq, now_s());
                fflush(stdout);
            }
        }
        if (poll(&pfd, 1, 20) <= 0)
            continue;
        if (!fgets(line, sizeof line, stdin))
            break;
        line[strcspn(line, "\r\n")] = 0;
        if (!line[0])
            continue;
        char msg[192];
        snprintf(msg, sizeof msg, "%.16s: %.120s", name, line);
        if (strlen(msg) > 27)
            msg[27] = 0;
        mbw(MB_CONTROL, 8);                   /* RX_STOP */
        uint8_t buf[64] = {0};
        int len = (int)strlen(msg);
        memcpy(buf, msg, len);
        mbw(MB_TX_SEQUENCE, (uint32_t)seq++);
        mbw(MB_TX_LENGTH, (uint32_t)len);
        for (int w = 0; w < 8; w++)
            mbw(MB_TX_DATA0 + 4 * w, buf[4 * w] | (buf[4 * w + 1] << 8) | (buf[4 * w + 2] << 16) | ((uint32_t)buf[4 * w + 3] << 24));
        /* The listening attempt in flight ends within its 136 ms window; TX_START is refused
         * until then, so retry until the mailbox reports TX_BUSY or TX_DONE. */
        double t_end = now_s() + 1.0;
        int started = 0;
        /* Wait out the listening attempt in flight (at most 136 ms) before TX_START (#70). Sending
         * as soon as the mailbox takes TX_START puts the burst at the end of our listening window,
         * and the other board's window started at the same moment as ours (both restarted on the
         * last exchange): the burst arrived at the very end of its window, and 7-9 % were lost.
         * After a fixed wait the burst goes out at a moment set by the typed line instead. */
        const char *dly = getenv("ZMBOX_TX_DELAY_MS");
        usleep((useconds_t)((dly ? atof(dly) : 140.0) * 1000.0));
        while (now_s() < t_end && !started) {
            mbw(MB_CONTROL, 1);
            /* TX_DONE stays set from the previous message, so only TX_BUSY tells that this
             * TX_START was taken; a send with its own reception lasts over a millisecond. */
            for (int i = 0; i < 200 && !started; i++)
                started = (mbr(MB_STATUS) & 0x1) != 0;
            if (!started)
                usleep(2000);
        }
        t_end = now_s() + 1.0;
        while (started && now_s() < t_end && !(mbr(MB_STATUS) & 0x4))
            usleep(500);
        if (mbr(MB_STATUS) & 0x4)
            take_rx(&rseq, &meta, out);       /* our own burst, heard on our own RX */
        printf(">> %s%s\n", msg, started ? "" : "   (not sent: mailbox busy)");
        fflush(stdout);
        mbw(MB_CONTROL, 4);                   /* RX_LISTEN again */
    }
    mbw(MB_CONTROL, 8);
    return 0;
}

static void stop(void)
{
    DIR *d = opendir("/proc");
    struct dirent *e;
    char p[300], comm[64];
    while (d && (e = readdir(d))) {
        int pid = atoi(e->d_name);
        if (pid <= 0)
            continue;
        snprintf(p, sizeof p, "/proc/%d/comm", pid);
        FILE *f = fopen(p, "r");
        if (!f)
            continue;
        if (fgets(comm, sizeof comm, f) && strncmp(comm, "iio_writedev", 12) == 0)
            kill(pid, SIGTERM);              /* SIGTERM: iio_writedev stops the DMA (Lab 11.48) */
        fclose(f);
    }
    if (d)
        closedir(d);
    attr("out_voltage0_hardwaregain", "-89.75");
    attr("out_altvoltage1_TX_LO_powerdown", "1");
    printf("transmitter stopped\n");
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: zmbox send <text> [--seq N] [--count N] [--tx-gain dB] [--rx-gain dB] [--lo Hz] [--offset N] [--quiet]\n"
                        "       zmbox listen [--count N] [--timeout s] [--rx-gain dB] [--lo Hz]\n"
                        "       zmbox chat [--name X] [--tx-gain dB] [--rx-gain dB] [--lo Hz]\n"
                        "       zmbox stop\n");
        return 2;
    }
    if (find_phy()) {
        fprintf(stderr, "ad9361-phy not found\n");
        return 2;
    }
    if (!strcmp(argv[1], "stop")) {
        stop();
        return 0;
    }
    int seq = 0, count = -1, rx_gain = -1, offset = 1, quiet = 0;
    double tx_gain = 0.0, timeout = 60.0;
    long lo = 915000000L;
    for (int i = strcmp(argv[1], "send") ? 2 : 3; i < argc; i++) {
        if (!strcmp(argv[i], "--seq") && i + 1 < argc) seq = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--timeout") && i + 1 < argc) timeout = atof(argv[++i]);
        else if (!strcmp(argv[i], "--count") && i + 1 < argc) count = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--tx-gain") && i + 1 < argc) tx_gain = atof(argv[++i]);
        else if (!strcmp(argv[i], "--rx-gain") && i + 1 < argc) rx_gain = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--lo") && i + 1 < argc) lo = atol(argv[++i]);
        else if (!strcmp(argv[i], "--offset") && i + 1 < argc) offset = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--quiet")) quiet = 1;
    }
    if (!strcmp(argv[1], "chat")) {
        const char *name = "?";
        for (int i = 2; i + 1 < argc; i++)
            if (!strcmp(argv[i], "--name"))
                name = argv[i + 1];
        if (open_regs())
            return 2;
        return chat(name, tx_gain, rx_gain < 0 ? 71 : rx_gain, lo);
    }
    if (!strcmp(argv[1], "listen")) {
        if (open_regs())
            return 2;
        return listen_loop(count < 0 ? 1000000 : count, timeout, rx_gain < 0 ? 71 : rx_gain, lo);
    }
    if (strcmp(argv[1], "send") || argc < 3) {
        fprintf(stderr, "unknown command\n");
        return 2;
    }
    if (count < 0)
        count = 1;
    if (rx_gain < 0)
        rx_gain = 60;
    if (open_regs())
        return 2;
    radio_setup(tx_gain, rx_gain, lo, offset);
    int ok = 0;
    for (int k = 0; k < count; k++)
        ok += send(argv[2], (seq + k) & 0xFFFF, quiet) == 0;
    if (count > 1)
        fprintf(stderr, "sent %d, delivered %d\n", count, ok);
    return ok == count ? 0 : 1;
}
