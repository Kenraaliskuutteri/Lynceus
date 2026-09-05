#ifndef LYNCEUS_METRICS_H
#define LYNCEUS_METRICS_H

#include <stdint.h>
#include <stddef.h>

typedef struct {
    int64_t timestamp_ms;
    double cpu_usage;
    double ram_usage;
    double disk_usage;
    double network_rx_kb;
    double network_tx_kb;
} system_metrics_t;

typedef struct {
    uint64_t total;
    uint64_t idle;
    uint64_t rx_bytes;
    uint64_t tx_bytes;
    int64_t timestamp_ms;
    int initialized;
} collector_state_t;

void collector_init(collector_state_t *state);
int collector_sample(collector_state_t *state, system_metrics_t *out);
int metrics_to_json(const system_metrics_t *m, char *buf, size_t buf_len);

#endif