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

static volatile sig_atomic_t g_running = 1;
static wsclient_t *g_client_instance = NULL;

static void handle_signal(int sig) {
    (void)sig;
    g_running = 0;
    if (g_client_instance) {
        wsclient_wake(g_client_instance);
    }
}

static void print_usage(const char *prog) {
    fprintf(stderr,
        "usage: %s [--config PATH] --host HOST --id SERVER_ID --key KEY\n"
        "       [--port PORT] [--interval SECONDS] [--tls] [--insecure]\n"
        "       [--daemon] [--pidfile PATH] [--log-file PATH]\n", prog);
}

typedef struct {
    collector_state_t collector;
    agent_config_t *cfg;
} agent_app_t;

static void on_sample_tick(wsclient_t *client, void *user_data) {
    agent_app_t *app = (agent_app_t *)user_data;
    system_metrics_t metrics;
    if (collector_sample(&app->collector, &metrics) == 0) {
        if (wsclient_is_connected(client)) {
            char json[512];
            int n = metrics_to_json(&metrics, json, sizeof(json));
            if (n > 0) {
                wsclient_send(client, json, (size_t)n);
            }
        }
    }
}

static void on_connection_state_changed(wsclient_t *client, int connected, void *user_data) {
    (void)client;
    agent_app_t *app = (agent_app_t *)user_data;
    printf(connected ? "connected to %s:%d\n" : "disconnected from %s:%d\n",
           app->cfg->host, app->cfg->port);
    fflush(stdout);
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

    agent_app_t app;
    app.cfg = &cfg;
    collector_init(&app.collector);

    wsclient_t *client = wsclient_create(cfg.host, cfg.port, path, cfg.use_tls, cfg.insecure_tls);
    if (!client) {
        fprintf(stderr, "failed to create websocket client\n");
        return 1;
    }

    g_client_instance = client;
    wsclient_set_connection_cb(client, on_connection_state_changed, &app);
    wsclient_set_periodic_timer(client, cfg.interval_sec * 1000, on_sample_tick, &app);

    while (g_running) {
        wsclient_service(client, 0);
    }

    g_client_instance = NULL;
    wsclient_destroy(client);
    return 0;
}