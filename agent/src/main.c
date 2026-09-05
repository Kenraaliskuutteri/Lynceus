#include "metrics.h"
#include "wsclient.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <getopt.h>
#include <time.h>

static volatile sig_atomic_t g_running = 1;

static void handle_signal(int sig) {
    (void)sig;
    g_running = 0;
}

static int64_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static void print_usage(const char *prog) {
    fprintf(stderr,
        "usage: %s --host HOST --id SERVER_ID --key KEY "
        "[--port PORT] [--interval SECONDS] [--tls] [--insecure]\n", prog);
}

int main(int argc, char **argv) {
    const char *host = NULL;
    int port = 8000;
    const char *server_id = NULL;
    const char *key = "";
    int interval_sec = 2;
    int use_tls = 0;
    int insecure_tls = 0;

    static struct option long_opts[] = {
        {"host", required_argument, 0, 'h'},
        {"port", required_argument, 0, 'p'},
        {"id", required_argument, 0, 'i'},
        {"key", required_argument, 0, 'k'},
        {"interval", required_argument, 0, 's'},
        {"tls", no_argument, 0, 't'},
        {"insecure", no_argument, 0, 'x'},
        {0, 0, 0, 0}
    };

    int opt;
    while ((opt = getopt_long(argc, argv, "h:p:i:k:s:tx", long_opts, NULL)) != -1) {
        switch (opt) {
            case 'h': host = optarg; break;
            case 'p': port = atoi(optarg); break;
            case 'i': server_id = optarg; break;
            case 'k': key = optarg; break;
            case 's': interval_sec = atoi(optarg); break;
            case 't': use_tls = 1; break;
            case 'x': insecure_tls = 1; break;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }

    if (!host || !server_id) {
        print_usage(argv[0]);
        return 1;
    }

    char path[512];
    snprintf(path, sizeof(path), "/api/v1/ws/metrics/%s?key=%s", server_id, key);

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    wsclient_t *client = wsclient_create(host, port, path, use_tls, insecure_tls);
    if (!client) {
        fprintf(stderr, "failed to create websocket client\n");
        return 1;
    }

    collector_state_t state;
    collector_init(&state);

    int64_t last_sample_ms = now_ms();
    int64_t interval_ms = (int64_t)interval_sec * 1000;

    while (g_running) {
        wsclient_service(client, 50);

        int64_t t = now_ms();
        if (t - last_sample_ms >= interval_ms) {
            if (wsclient_is_connected(client)) {
                system_metrics_t metrics;
                if (collector_sample(&state, &metrics) == 0) {
                    char json[512];
                    int n = metrics_to_json(&metrics, json, sizeof(json));
                    if (n > 0) {
                        wsclient_send(client, json, (size_t)n);
                    }
                }
            }
            last_sample_ms = t;
        }
    }

    wsclient_destroy(client);
    return 0;
}