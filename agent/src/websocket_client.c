#include "wsclient.h"

#include <libwebsockets.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define RECONNECT_DELAY_MS 3000 // If you arent happy with waiting 30seconds then tough luck.

struct wsclient {
    struct lws_context *context;
    struct lws *wsi;
    struct lws_protocols protocols[2];
    char host[256];
    char path[512];
    int port;
    int use_tls;
    int insecure_tls;
    int connected;
    int64_t last_connect_attempt_ms;
    unsigned char *pending;
    size_t pending_len;
    size_t pending_capacity;
};

static wsclient_t *g_client = NULL;

static int64_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static int lws_event_callback(struct lws *wsi, enum lws_callback_reasons reason,
                               void *user, void *in, size_t len) {
    (void)user;
    (void)in;
    (void)len;

    if (!g_client) return 0;

    switch (reason) {
        case LWS_CALLBACK_CLIENT_ESTABLISHED:
            g_client->connected = 1;
            break;

        case LWS_CALLBACK_CLIENT_WRITEABLE:
            if (g_client->pending_len > 0) {
                lws_write(wsi, g_client->pending + LWS_PRE, g_client->pending_len,
                          LWS_WRITE_TEXT);
                g_client->pending_len = 0;
            }
            break;

        case LWS_CALLBACK_CLIENT_CONNECTION_ERROR:
        case LWS_CALLBACK_CLOSED:
            g_client->connected = 0;
            g_client->wsi = NULL;
            break;

        default:
            break;
    }

    return 0;
}

static void try_connect(wsclient_t *client) {
    struct lws_client_connect_info info;
    memset(&info, 0, sizeof(info));

    int ssl_flags = 0;
    if (client->use_tls) {
        ssl_flags = LCCSCF_USE_SSL;
        if (client->insecure_tls) {
            ssl_flags |= LCCSCF_ALLOW_SELFSIGNED | LCCSCF_ALLOW_INSECURE;
        }
    }

    info.context = client->context;
    info.address = client->host;
    info.port = client->port;
    info.path = client->path;
    info.host = client->host;
    info.origin = client->host;
    info.protocol = client->protocols[0].name;
    info.ssl_connection = ssl_flags;
    info.pwsi = &client->wsi;

    client->wsi = NULL;
    lws_client_connect_via_info(&info);
    client->last_connect_attempt_ms = now_ms();
}

wsclient_t *wsclient_create(const char *host, int port, const char *path, int use_tls, int insecure_tls) {
    wsclient_t *client = calloc(1, sizeof(wsclient_t));
    if (!client) return NULL;

    snprintf(client->host, sizeof(client->host), "%s", host);
    snprintf(client->path, sizeof(client->path), "%s", path);
    client->port = port;
    client->use_tls = use_tls;
    client->insecure_tls = insecure_tls;

    client->protocols[0].name = "lynceus-daemon";
    client->protocols[0].callback = lws_event_callback;
    client->protocols[0].per_session_data_size = 0;
    client->protocols[0].rx_buffer_size = 4096;
    client->protocols[1].name = NULL;

    struct lws_context_creation_info ctx_info;
    memset(&ctx_info, 0, sizeof(ctx_info));
    ctx_info.port = CONTEXT_PORT_NO_LISTEN;
    ctx_info.protocols = client->protocols;
    ctx_info.options = LWS_SERVER_OPTION_DO_SSL_GLOBAL_INIT;

    client->context = lws_create_context(&ctx_info);
    if (!client->context) {
        free(client);
        return NULL;
    }

    g_client = client;
    try_connect(client);

    return client;
}

int wsclient_service(wsclient_t *client, int timeout_ms) {
    if (!client) return -1;

    if (!client->connected && !client->wsi) {
        if (now_ms() - client->last_connect_attempt_ms >= RECONNECT_DELAY_MS) {
            try_connect(client);
        }
    }

    lws_service(client->context, timeout_ms);
    return client->connected;
}

int wsclient_send(wsclient_t *client, const char *data, size_t len) {
    if (!client || !client->connected || !client->wsi) return -1;

    size_t needed = LWS_PRE + len;
    if (needed > client->pending_capacity) {
        unsigned char *buf = realloc(client->pending, needed);
        if (!buf) return -1;
        client->pending = buf;
        client->pending_capacity = needed;
    }

    memcpy(client->pending + LWS_PRE, data, len);
    client->pending_len = len;

    lws_callback_on_writable(client->wsi);
    return 0;
}

int wsclient_is_connected(wsclient_t *client) {
    return client && client->connected;
}

void wsclient_destroy(wsclient_t *client) {
    if (!client) return;
    if (client->context) lws_context_destroy(client->context);
    free(client->pending);
    if (g_client == client) g_client = NULL;
    free(client);
}