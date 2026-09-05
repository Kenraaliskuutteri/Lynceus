#include "metrics.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <inttypes.h>
#include <sys/statvfs.h>

static int64_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static int read_cpu_totals(uint64_t *total, uint64_t *idle) {
    FILE *f = fopen("/proc/stat", "r");
    if (!f) return -1;

    char label[16];
    uint64_t user, nice, system, idle_v, iowait, irq, softirq, steal;
    int n = fscanf(f, "%15s %" SCNu64 " %" SCNu64 " %" SCNu64 " %" SCNu64
                       " %" SCNu64 " %" SCNu64 " %" SCNu64 " %" SCNu64,
                   label, &user, &nice, &system, &idle_v, &iowait, &irq, &softirq, &steal);
    fclose(f);

    if (n < 8) return -1;

    *idle = idle_v + iowait;
    *total = user + nice + system + idle_v + iowait + irq + softirq + steal;
    return 0;
}

static int read_ram_usage(double *usage) {
    FILE *f = fopen("/proc/meminfo", "r");
    if (!f) return -1;

    char line[256];
    uint64_t mem_total = 0, mem_available = 0;
    int found = 0;

    while (fgets(line, sizeof(line), f)) {
        uint64_t value;
        if (sscanf(line, "MemTotal: %" SCNu64 " kB", &value) == 1) {
            mem_total = value;
            found++;
        } else if (sscanf(line, "MemAvailable: %" SCNu64 " kB", &value) == 1) {
            mem_available = value;
            found++;
        }
        if (found == 2) break;
    }
    fclose(f);

    if (mem_total == 0) return -1;

    *usage = 100.0 * (1.0 - ((double)mem_available / (double)mem_total));
    return 0;
}

static int read_disk_usage(double *usage) {
    struct statvfs st;
    if (statvfs("/", &st) != 0) return -1;
    if (st.f_blocks == 0) return -1;

    *usage = 100.0 * (1.0 - ((double)st.f_bavail / (double)st.f_blocks));
    return 0;
}

static int read_network_totals(uint64_t *rx, uint64_t *tx) {
    FILE *f = fopen("/proc/net/dev", "r");
    if (!f) return -1;

    char line[512];
    uint64_t rx_total = 0, tx_total = 0;

    if (!fgets(line, sizeof(line), f) || !fgets(line, sizeof(line), f)) {
        fclose(f);
        return -1;
    }

    while (fgets(line, sizeof(line), f)) {
        char iface[64];
        uint64_t rx_bytes, tx_bytes;
        uint64_t rx_p, rx_e, rx_d, rx_f, rx_c, rx_fr, rx_co;
        uint64_t tx_p;

        char *colon = strchr(line, ':');
        if (!colon) continue;
        *colon = ' ';

        int n = sscanf(line, "%63s %" SCNu64 " %" SCNu64 " %" SCNu64 " %" SCNu64
                             " %" SCNu64 " %" SCNu64 " %" SCNu64 " %" SCNu64
                             " %" SCNu64 " %" SCNu64,
                       iface, &rx_bytes, &rx_p, &rx_e, &rx_d, &rx_f, &rx_c, &rx_fr, &rx_co,
                       &tx_bytes, &tx_p);
        if (n < 11) continue;
        if (strcmp(iface, "lo") == 0) continue;

        rx_total += rx_bytes;
        tx_total += tx_bytes;
    }
    fclose(f);

    *rx = rx_total;
    *tx = tx_total;
    return 0;
}

void collector_init(collector_state_t *state) {
    memset(state, 0, sizeof(*state));

    uint64_t total = 0, idle = 0, rx = 0, tx = 0;
    read_cpu_totals(&total, &idle);
    read_network_totals(&rx, &tx);

    state->total = total;
    state->idle = idle;
    state->rx_bytes = rx;
    state->tx_bytes = tx;
    state->timestamp_ms = now_ms();
    state->initialized = 1;
}

int collector_sample(collector_state_t *state, system_metrics_t *out) {
    if (!state->initialized) return -1;

    int64_t ts = now_ms();
    double elapsed_sec = (double)(ts - state->timestamp_ms) / 1000.0;
    if (elapsed_sec <= 0) elapsed_sec = 1.0;

    uint64_t total = 0, idle = 0;
    double cpu_usage = 0.0;
    if (read_cpu_totals(&total, &idle) == 0) {
        uint64_t total_delta = (total > state->total) ? total - state->total : 0;
        uint64_t idle_delta = (idle > state->idle) ? idle - state->idle : 0;
        if (total_delta > 0) {
            cpu_usage = 100.0 * (1.0 - ((double)idle_delta / (double)total_delta));
        }
    }

    double ram_usage = 0.0;
    read_ram_usage(&ram_usage);

    double disk_usage = 0.0;
    read_disk_usage(&disk_usage);

    uint64_t rx = 0, tx = 0;
    double rx_kb = 0.0, tx_kb = 0.0;
    if (read_network_totals(&rx, &tx) == 0) {
        uint64_t rx_delta = (rx > state->rx_bytes) ? rx - state->rx_bytes : 0;
        uint64_t tx_delta = (tx > state->tx_bytes) ? tx - state->tx_bytes : 0;
        rx_kb = ((double)rx_delta / 1024.0) / elapsed_sec;
        tx_kb = ((double)tx_delta / 1024.0) / elapsed_sec;
    }

    out->timestamp_ms = ts;
    out->cpu_usage = cpu_usage;
    out->ram_usage = ram_usage;
    out->disk_usage = disk_usage;
    out->network_rx_kb = rx_kb;
    out->network_tx_kb = tx_kb;

    state->total = total;
    state->idle = idle;
    state->rx_bytes = rx;
    state->tx_bytes = tx;
    state->timestamp_ms = ts;

    return 0;
}

int metrics_to_json(const system_metrics_t *m, char *buf, size_t buf_len) {
    int n = snprintf(buf, buf_len,
        "{\"timestamp\":%" PRId64 ",\"cpuUsage\":%.1f,\"ramUsage\":%.1f,"
        "\"diskUsage\":%.1f,\"networkRxKb\":%.1f,\"networkTxKb\":%.1f}",
        m->timestamp_ms, m->cpu_usage, m->ram_usage,
        m->disk_usage, m->network_rx_kb, m->network_tx_kb);

    if (n < 0 || (size_t)n >= buf_len) return -1;
    return n;
}