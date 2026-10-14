/*
 * Issue #48, Lab 8.14 stage 3: drive the PS + AXI DMA + OFDM modem block design
 * (tools/build_block8_ofdm_dma_bd.py) from Linux user space on the board.
 *
 *   DDR --MM2S--> modem S_AXIS_TX -> fabric loopback -> modem M_AXIS_RX --S2MM--> DDR
 *
 * No kernel driver: registers and buffers are reached through /dev/mem.
 *   modem registers  0x40000000 (see ofdm_axi_modem.v for the map)
 *   AXI DMA          0x40400000 (simple mode, interrupts left disabled, polled)
 *
 * DMA buffers. The DMA needs physical addresses. The program locks one page per
 * buffer in its own address space, so the kernel cannot reuse it, and looks up
 * its physical frame in /proc/self/pagemap. The HP0 port is not coherent with
 * the CPU caches, so the program never touches the buffers through the cached
 * mapping after allocation: it sweeps a large scratch area to evict any dirty
 * lines left by the kernel's page clearing, then reads and writes the buffers
 * only through an uncached /dev/mem mapping (O_SYNC).
 *
 * Framing. After a modem reset the first CE_TRAIN_SYMBOLS received symbols
 * train the channel equalizer and produce no output, so the TX stream is the
 * train_bits() pattern for that many symbols, then the data. The modem puts
 * tlast on every 48th output byte, and an S2MM transfer in simple mode ends at
 * tlast, so the receive side is one 48-byte transfer per OFDM symbol. Each
 * output byte is {data_index[5:0], bits[1:0]}, in FFT bin order.
 *
 * Build:  arm-linux-gnueabihf-gcc -O2 -static -o ofdm_dma_loopback ofdm_dma_loopback.c
 * Run:    ./ofdm_dma_loopback [symbols per run, 1..80] [runs] [seed]
 * Prints one line of JSON and exits 0 only if every bit came back.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define MODEM_BASE 0x40000000u
#define DMA_BASE 0x40400000u
#define PAGE 4096u
#define PAIRS_PER_SYMBOL 48u

/* modem registers */
#define M_ID 0x00
#define M_VERSION 0x04
#define M_CONTROL 0x08
#define M_STATUS 0x0C
#define M_TX_SAT 0x10
#define M_FFT_SAT 0x14
#define M_EQ_SAT 0x18
#define M_TX_SYMBOLS 0x1C
#define M_RX_SYMBOLS 0x20
#define M_CE_SAT 0x2C
#define M_CE_TRAINED 0x30
#define M_CONFIG 0x38

/* AXI DMA simple mode registers (PG021) */
#define MM2S_DMACR 0x00
#define MM2S_DMASR 0x04
#define MM2S_SA 0x18
#define MM2S_LENGTH 0x28
#define S2MM_DMACR 0x30
#define S2MM_DMASR 0x34
#define S2MM_DA 0x48
#define S2MM_LENGTH 0x58
#define DMACR_RS 0x1u
#define DMACR_RESET 0x4u
#define DMASR_ERRORS 0x770u /* DMAIntErr, DMASlvErr, DMADecErr, SGIntErr, SGSlvErr, SGDecErr */
#define DMASR_IOC 0x1000u

static volatile uint32_t *modem, *dma;
static int memfd;

static uint32_t rd(volatile uint32_t *base, uint32_t off) { return base[off / 4]; }
static void wr(volatile uint32_t *base, uint32_t off, uint32_t v) { base[off / 4] = v; }

static void *map_phys(uint32_t phys, uint32_t len)
{
    void *p = mmap(NULL, len, PROT_READ | PROT_WRITE, MAP_SHARED, memfd, phys);
    if (p == MAP_FAILED) {
        perror("mmap /dev/mem");
        exit(2);
    }
    return p;
}

/* Lock one page and return its physical address. */
static uint32_t locked_page(void)
{
    uint8_t *p = mmap(NULL, PAGE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_LOCKED | MAP_POPULATE, -1, 0);
    uint64_t entry;
    int fd;
    if (p == MAP_FAILED || mlock(p, PAGE) != 0) {
        perror("lock page");
        exit(2);
    }
    p[0] = 0; /* make sure it is faulted in */
    fd = open("/proc/self/pagemap", O_RDONLY);
    if (fd < 0 || pread(fd, &entry, 8, ((uintptr_t)p / PAGE) * 8) != 8) {
        perror("pagemap");
        exit(2);
    }
    close(fd);
    if (!(entry >> 63) || (entry & ((1ull << 55) - 1)) == 0) {
        fprintf(stderr, "page not present or PFN hidden (run as root)\n");
        exit(2);
    }
    return (uint32_t)((entry & ((1ull << 55) - 1)) * PAGE);
}

static void evict_caches(void)
{
    /* 4 MB: eight times the 512 KB L2, so dirty lines of the DMA pages are written back. */
    size_t n = 4u << 20;
    volatile uint8_t *s = malloc(n);
    size_t i;
    for (i = 0; i < n; i += 32)
        s[i] = (uint8_t)i;
    free((void *)s);
}

static int wait_idle(uint32_t sr_off, uint32_t *sr_out)
{
    uint32_t sr = 0;
    long spins;
    for (spins = 0; spins < 2000000; spins++) {
        sr = rd(dma, sr_off);
        if (sr & DMASR_ERRORS)
            break;
        if (sr & DMASR_IOC) /* set on completion even with interrupts disabled */
            break;
    }
    *sr_out = sr;
    return (sr & DMASR_ERRORS) || !(sr & DMASR_IOC) ? -1 : 0;
}

static uint8_t train_bits(unsigned d)
{
    unsigned i = ((d >> 0) ^ (d >> 3)) & 1u;
    unsigned q = ((d >> 1) ^ (d >> 2) ^ (d >> 4)) & 1u;
    return (uint8_t)((i << 1) | q);
}

static uint32_t rng_state;
static uint32_t rng(void)
{
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 17;
    rng_state ^= rng_state << 5;
    return rng_state;
}

int main(int argc, char **argv)
{
    unsigned symbols = argc > 1 ? (unsigned)atoi(argv[1]) : 40;
    unsigned runs = argc > 2 ? (unsigned)atoi(argv[2]) : 10;
    unsigned seed = argc > 3 ? (unsigned)strtoul(argv[3], NULL, 0) : 0x48D5;
    uint32_t tx_phys, rx_phys, config, train, sr;
    volatile uint8_t *tx, *rx;
    uint8_t sent[PAGE];
    unsigned run, k, s, b;
    unsigned long bits = 0, bit_errors = 0, missing = 0, symbols_ok = 0;
    unsigned failed_runs = 0, dma_errors = 0;
    uint32_t sat_tx = 0, sat_fft = 0, sat_eq = 0, sat_ce = 0, status = 0;
    struct timespec t0, t1;
    double dma_us = 0;

    memfd = open("/dev/mem", O_RDWR | O_SYNC);
    if (memfd < 0) {
        perror("/dev/mem");
        return 2;
    }
    modem = map_phys(MODEM_BASE, PAGE);
    dma = map_phys(DMA_BASE, 0x10000);
    if (rd(modem, M_ID) != 0x4F46444Du) {
        fprintf(stderr, "no OFDM modem at 0x%08x (ID 0x%08x)\n", MODEM_BASE, rd(modem, M_ID));
        return 2;
    }
    config = rd(modem, M_CONFIG);
    train = (config >> 5) & 0xFu;
    if (symbols < 1 || (train + symbols) * PAIRS_PER_SYMBOL > PAGE) {
        fprintf(stderr, "symbols per run must be 1..%u\n", PAGE / PAIRS_PER_SYMBOL - train);
        return 2;
    }

    tx_phys = locked_page();
    rx_phys = locked_page();
    evict_caches();
    tx = map_phys(tx_phys, PAGE);
    rx = map_phys(rx_phys, PAGE);
    rng_state = seed ? seed : 1;

    for (run = 0; run < runs; run++) {
        unsigned n_tx = (train + symbols) * PAIRS_PER_SYMBOL;
        unsigned run_errors = 0;

        for (k = 0; k < train * PAIRS_PER_SYMBOL; k++)
            tx[k] = train_bits(k % PAIRS_PER_SYMBOL);
        for (k = 0; k < symbols * PAIRS_PER_SYMBOL; k++) {
            sent[k] = (uint8_t)(rng() & 3u);
            tx[train * PAIRS_PER_SYMBOL + k] = sent[k];
        }
        for (k = 0; k < symbols * PAIRS_PER_SYMBOL; k++)
            rx[k] = 0xFF;

        /* Reset the modem datapath (also arms training) and both DMA channels. */
        wr(modem, M_CONTROL, 1);
        wr(modem, M_CONTROL, 0);
        wr(dma, MM2S_DMACR, DMACR_RESET);
        while (rd(dma, MM2S_DMACR) & DMACR_RESET)
            ;
        wr(dma, MM2S_DMACR, DMACR_RS);
        wr(dma, S2MM_DMACR, DMACR_RS);

        clock_gettime(CLOCK_MONOTONIC, &t0);
        wr(dma, MM2S_SA, tx_phys);
        wr(dma, MM2S_LENGTH, n_tx);
        for (s = 0; s < symbols; s++) {
            wr(dma, S2MM_DA, rx_phys + s * PAIRS_PER_SYMBOL);
            wr(dma, S2MM_LENGTH, PAIRS_PER_SYMBOL);
            if (wait_idle(S2MM_DMASR, &sr) != 0) {
                fprintf(stderr, "run %u symbol %u: S2MM status 0x%08x\n", run, s, sr);
                dma_errors++;
                break;
            }
            if (rd(dma, S2MM_LENGTH) != PAIRS_PER_SYMBOL)
                fprintf(stderr, "run %u symbol %u: S2MM length %u\n", run, s, rd(dma, S2MM_LENGTH));
            wr(dma, S2MM_DMASR, DMASR_IOC); /* clear */
        }
        if (wait_idle(MM2S_DMASR, &sr) != 0) {
            fprintf(stderr, "run %u: MM2S status 0x%08x\n", run, sr);
            dma_errors++;
        }
        wr(dma, MM2S_DMASR, DMASR_IOC);
        clock_gettime(CLOCK_MONOTONIC, &t1);
        dma_us += (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;

        /* Check: every symbol must return each of its 48 data indices once, with the sent bits. */
        for (s = 0; s < symbols; s++) {
            uint8_t seen[PAIRS_PER_SYMBOL] = {0};
            unsigned bad = 0;
            for (b = 0; b < PAIRS_PER_SYMBOL; b++) {
                uint8_t v = rx[s * PAIRS_PER_SYMBOL + b];
                unsigned idx = v >> 2;
                if (idx >= PAIRS_PER_SYMBOL || seen[idx]) {
                    bad++;
                    continue;
                }
                seen[idx] = 1;
                bit_errors += __builtin_popcount((v ^ sent[s * PAIRS_PER_SYMBOL + idx]) & 3u);
                run_errors += __builtin_popcount((v ^ sent[s * PAIRS_PER_SYMBOL + idx]) & 3u);
            }
            missing += bad;
            if (bad == 0)
                symbols_ok++;
            run_errors += bad;
        }
        bits += symbols * PAIRS_PER_SYMBOL * 2;
        failed_runs += run_errors != 0;
        sat_tx += rd(modem, M_TX_SAT);
        sat_fft += rd(modem, M_FFT_SAT);
        sat_eq += rd(modem, M_EQ_SAT);
        sat_ce += rd(modem, M_CE_SAT);
        status |= rd(modem, M_STATUS) & 0x18u; /* sticky frame errors */
        if (run == runs - 1)
            status |= rd(modem, M_STATUS) & 0x40u;
    }

    printf("{\"id\": \"0x%08x\", \"version\": \"0x%08x\", \"config\": \"0x%08x\", "
           "\"tx_phys\": \"0x%08x\", \"rx_phys\": \"0x%08x\", \"symbols_per_run\": %u, \"runs\": %u, "
           "\"seed\": %u, \"bits\": %lu, \"bit_errors\": %lu, \"missing_or_duplicate_bytes\": %lu, "
           "\"symbols_complete\": %lu, \"failed_runs\": %u, \"dma_errors\": %u, "
           "\"tx_symbols_last_run\": %u, \"rx_symbols_last_run\": %u, \"ce_trained_last_run\": %u, "
           "\"saturations\": {\"tx\": %u, \"fft\": %u, \"eq\": %u, \"ce\": %u}, "
           "\"status_frame_error_bits\": \"0x%02x\", \"trained\": %u, \"dma_time_us_per_run\": %.1f}\n",
           rd(modem, M_ID), rd(modem, M_VERSION), config, tx_phys, rx_phys, symbols, runs, seed,
           bits, bit_errors, missing, symbols_ok, failed_runs, dma_errors,
           rd(modem, M_TX_SYMBOLS), rd(modem, M_RX_SYMBOLS), rd(modem, M_CE_TRAINED),
           sat_tx, sat_fft, sat_eq, sat_ce, status & 0x18u, (status >> 6) & 1u, dma_us / runs);
    return (bit_errors || missing || dma_errors || failed_runs) ? 1 : 0;
}
