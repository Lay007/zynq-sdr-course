/*
 * Board B: keep the vendor DAC stream running with zeros.
 *
 * Board B's device tree has no DAC driver, so nothing ever starts the TX DMA. The course
 * mux (course_dac_fifo_source_mux.v) writes the DAC FIFO on the vendor stream's strobe and only
 * substitutes the modem burst while it transmits; with the vendor stream dead it falls back to
 * writing only during the burst, so between bursts the DAC holds the last burst sample and
 * radiates a carrier at the TX LO. This program runs the ADI axi_dmac at 0x7c420000 (memory ->
 * DAC stream) in cyclic mode over one locked page of zeros, so the FIFO is written with zeros at
 * the DAC rate between bursts, as the mux expects.
 *
 * Build: arm-linux-gnueabihf-gcc -O2 -static -o dac_zero_stream dac_zero_stream.c
 * Run:   ./dac_zero_stream &      Stop: kill <pid>   (SIGTERM/SIGINT stop the DMA before exiting;
 *        never kill -9: the DMA would keep reading a page the kernel may reuse)
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define DMAC_BASE 0x7c420000u
#define PAGE 4096u
#define R_IRQ_MASK 0x080
#define R_CTRL 0x400
#define R_TRANSFER_SUBMIT 0x408
#define R_FLAGS 0x40C
#define R_SRC_ADDRESS 0x414
#define R_X_LENGTH 0x418
#define R_Y_LENGTH 0x41C
#define R_SRC_STRIDE 0x424
#define FLAG_CYCLIC 0x1u

static volatile uint32_t *dmac;
static volatile sig_atomic_t stop;

static void on_signal(int s) { (void)s; stop = 1; }
static void wr(uint32_t off, uint32_t v) { dmac[off / 4] = v; }

int main(void)
{
    int memfd = open("/dev/mem", O_RDWR | O_SYNC);
    uint8_t *page;
    uint64_t entry;
    uint32_t phys;
    volatile uint8_t *zero;
    int fd;
    unsigned i;

    if (memfd < 0) { perror("/dev/mem"); return 2; }
    dmac = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE, MAP_SHARED, memfd, DMAC_BASE);
    if (dmac == MAP_FAILED) { perror("mmap dmac"); return 2; }

    page = mmap(NULL, PAGE, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_LOCKED | MAP_POPULATE, -1, 0);
    if (page == MAP_FAILED || mlock(page, PAGE) != 0) { perror("lock page"); return 2; }
    page[0] = 0;
    fd = open("/proc/self/pagemap", O_RDONLY);
    if (fd < 0 || pread(fd, &entry, 8, ((uintptr_t)page / PAGE) * 8) != 8 || !(entry >> 63)) {
        perror("pagemap"); return 2;
    }
    close(fd);
    phys = (uint32_t)((entry & ((1ull << 55) - 1)) * PAGE);
    {   /* push dirty lines of the page out of the caches, then write zeros uncached */
        size_t n = 4u << 20; volatile uint8_t *s = malloc(n);
        for (i = 0; i < n; i += 32) s[i] = (uint8_t)i;
        free((void *)s);
    }
    zero = mmap(NULL, PAGE, PROT_READ | PROT_WRITE, MAP_SHARED, memfd, phys);
    if (zero == MAP_FAILED) { perror("mmap page"); return 2; }
    for (i = 0; i < PAGE; i++) zero[i] = 0;

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);
    signal(SIGHUP, on_signal);

    wr(R_CTRL, 0);                 /* reset the core */
    wr(R_IRQ_MASK, 0x3);           /* no interrupts: nobody services them */
    wr(R_CTRL, 1);                 /* enable */
    wr(R_FLAGS, FLAG_CYCLIC);
    wr(R_SRC_ADDRESS, phys);
    wr(R_SRC_STRIDE, 0);
    wr(R_X_LENGTH, PAGE - 1);
    wr(R_Y_LENGTH, 0);
    wr(R_TRANSFER_SUBMIT, 1);
    printf("dac_zero_stream: cyclic zeros from 0x%08x, pid %d\n", phys, (int)getpid());
    fflush(stdout);

    while (!stop)
        pause();
    wr(R_CTRL, 0);                 /* stop the DMA before the page goes back to the kernel */
    printf("dac_zero_stream: stopped\n");
    return 0;
}
