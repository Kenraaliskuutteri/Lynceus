#include "metrics.h"
#include "wsclient.h"
#include "config.h"
#include "daemon.h"

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
        "usage: %s [--config PATH] --host HOST --id SERVER_ID --key KEY\n"
        "       [--port PORT] [--interval SECONDS] [--tls] [--insecure]\n"
        "       [--daemon] [--pidfile PATH] [--log-file PATH]\n", prog);
}

int main(int argc, char **argv) {
    agent_config_t cfg;
    config_set_defaults(&cfg);

    for (int i = 1; i < argc - 1; i++) {
        if (strcmp(argv[i], "-c") == 0 || strcmp(argv[i], "--config") == 0) {
            config_load_file(&cfg, argv[i + 1]);
            break;
        }
    }

    static struct option long_opts[] = {
        {"config", required_argument, 0, 'c'},
        {"host", required_argument, 0, 'h'},
        {"port", required_argument, 0, 'p'},
        {"id", required_argument, 0, 'i'},
        {"key", required_argument, 0, 'k'},
        {"interval", required_argument, 0, 's'},
        {"tls", no_argument, 0, 't'},
        {"insecure", no_argument, 0, 'x'},
        {"daemon", no_argument, 0, 'd'},
        {"pidfile", required_argument, 0, 'P'},
        {"log-file", required_argument, 0, 'L'},
        {0, 0, 0, 0}
    };

    int opt;
    optind = 1;
    while ((opt = getopt_long(argc, argv, "c:h:p:i:k:s:txdP:L:", long_opts, NULL)) != -1) {
        switch (opt) {
            case 'c': break;
            case 'h': snprintf(cfg.host, sizeof(cfg.host), "%s", optarg); break;
            case 'p': cfg.port = atoi(optarg); break;
            case 'i': snprintf(cfg.server_id, sizeof(cfg.server_id), "%s", optarg); break;
            case 'k': snprintf(cfg.key, sizeof(cfg.key), "%s", optarg); break;
            case 's': cfg.interval_sec = atoi(optarg); break;
            case 't': cfg.use_tls = 1; break;
            case 'x': cfg.insecure_tls = 1; break;
            case 'd': cfg.daemonize = 1; break;
            case 'P': snprintf(cfg.pidfile, sizeof(cfg.pidfile), "%s", optarg); break;
            case 'L': snprintf(cfg.log_file, sizeof(cfg.log_file), "%s", optarg); break;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }

    if (cfg.host[0] == '\0' || cfg.server_id[0] == '\0') {
        print_usage(argv[0]);
        return 1;
    }

    char path[512];
    snprintf(path, sizeof(path), "/api/v1/ws/metrics/%s?key=%s", cfg.server_id, cfg.key);

    if (cfg.daemonize) {
        if (daemonize(cfg.pidfile, cfg.log_file) != 0) {
            fprintf(stderr, "failed to daemonize\n");
            return 1;
        }
    }

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    wsclient_t *client = wsclient_create(cfg.host, cfg.port, path, cfg.use_tls, cfg.insecure_tls);
    if (!client) {
        fprintf(stderr, "failed to create websocket client\n");
        return 1;
    }

    collector_state_t state;
    collector_init(&state);

    int64_t last_sample_ms = now_ms();
    int64_t interval_ms = (int64_t)cfg.interval_sec * 1000;
    int was_connected = 0;

    while (g_running) {
        wsclient_service(client, 50);

        int is_connected = wsclient_is_connected(client);
        if (is_connected != was_connected) {
            printf(is_connected ? "connected to %s:%d\n" : "disconnected from %s:%d\n",
                   cfg.host, cfg.port);
            fflush(stdout);
            was_connected = is_connected;
        }

        int64_t t = now_ms();
        if (t - last_sample_ms >= interval_ms) {
            fprintf(stderr, "sample attempt at t=%lld (delta=%lld ms)\n", (long long)t, (long long)(t - last_sample_ms));
            if (is_connected) {
                system_metrics_t metrics;
                if (collector_sample(&state, &metrics) == 0) {
                    char json[512];
                    int n = metrics_to_json(&metrics, json, sizeof(json));
                    if (n > 0) {
                        int rc = wsclient_send(client, json, (size_t)n);
                        fprintf(stderr, "wsclient_send rc=%d\n", rc);
                    }
                }
            }
            last_sample_ms = t;
        }
    }

    wsclient_destroy(client);
    return 0;
}