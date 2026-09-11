#include "wsclient.h"

#include <libwebsockets.h>
#include <stdlib.h>
#include <string.h>

#define RECONNECT_DELAY_MS 3000
#define MAX_QUEUE_DEPTH 50

typedef struct msg_queue_item {
    unsigned char *buf;
    size_t len;
    struct msg_queue_item *next;
} msg_queue_item_t;

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

    lws_sorted_usec_list_t sul_reconnect;
    lws_sorted_usec_list_t sul_timer;

    wsclient_timer_cb timer_cb;
    void *timer_user_data;
    int timer_interval_ms;

    wsclient_conn_cb conn_cb;
    void *conn_user_data;

    msg_queue_item_t *queue_head;
    msg_queue_item_t *queue_tail;
    size_t queue_count;
};

static void try_connect(wsclient_t *client);

static void on_reconnect_timer(lws_sorted_usec_list_t *sul) {
    wsclient_t *client = lws_container_of(sul, wsclient_t, sul_reconnect);
    if (!client->connected && !client->wsi) {
        try_connect(client);
    }
}

static void on_sample_timer(lws_sorted_usec_list_t *sul) {
    wsclient_t *client = lws_container_of(sul, wsclient_t, sul_timer);
    if (client->timer_cb) {
        client->timer_cb(client, client->timer_user_data);
    }
    lws_sul_schedule(client->context, 0, &client->sul_timer,
                     on_sample_timer, (lws_usec_t)client->timer_interval_ms * LWS_US_PER_MS);
}

static void clear_queue(wsclient_t *client) {
    while (client->queue_head) {
        msg_queue_item_t *item = client->queue_head;
        client->queue_head = item->next;
        free(item->buf);
        free(item);
    }
    client->queue_tail = NULL;
    client->queue_count = 0;
}

static int lws_event_callback(struct lws *wsi, enum lws_callback_reasons reason,
                               void *user, void *in, size_t len) {
    (void)user;
    (void)in;
    (void)len;

    struct lws_context *ctx = lws_get_context(wsi);
    wsclient_t *client = (wsclient_t *)lws_context_user(ctx);
    if (!client) return 0;

    switch (reason) {
        case LWS_CALLBACK_CLIENT_ESTABLISHED:
            client->connected = 1;
            lws_sul_cancel(&client->sul_reconnect);
            if (client->conn_cb) {
                client->conn_cb(client, 1, client->conn_user_data);
            }
            if (client->queue_head) {
                lws_callback_on_writable(wsi);
            }
            break;

        case LWS_CALLBACK_CLIENT_WRITEABLE:
            while (client->queue_head) {
                msg_queue_item_t *item = client->queue_head;
                int n = lws_write(wsi, item->buf + LWS_PRE, item->len, LWS_WRITE_TEXT);
                if (n < 0) {
                    break;
                }
                client->queue_head = item->next;
                if (!client->queue_head) {
                    client->queue_tail = NULL;
                }
                free(item->buf);
                free(item);
                client->queue_count--;

                if (lws_send_pipe_choked(wsi)) {
                    lws_callback_on_writable(wsi);
                    break;
                }
            }
            break;

        case LWS_CALLBACK_CLIENT_CONNECTION_ERROR:
        case LWS_CALLBACK_CLOSED: {
            int was_connected = client->connected;
            client->connected = 0;
            client->wsi = NULL;
            clear_queue(client);
            if (was_connected && client->conn_cb) {
                client->conn_cb(client, 0, client->conn_user_data);
            }
            lws_sul_schedule(client->context, 0, &client->sul_reconnect,
                             on_reconnect_timer, (lws_usec_t)RECONNECT_DELAY_MS * LWS_US_PER_MS);
            break;
        }

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
    info.userdata = client;

    client->wsi = NULL;
    if (!lws_client_connect_via_info(&info)) {
        lws_sul_schedule(client->context, 0, &client->sul_reconnect,
                         on_reconnect_timer, (lws_usec_t)RECONNECT_DELAY_MS * LWS_US_PER_MS);
    }
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
    ctx_info.user = client;

    client->context = lws_create_context(&ctx_info);
    if (!client->context) {
        free(client);
        return NULL;
    }

    try_connect(client);
    return client;
}

int wsclient_set_periodic_timer(wsclient_t *client, int interval_ms, wsclient_timer_cb cb, void *user_data) {
    if (!client || interval_ms <= 0) return -1;

    client->timer_cb = cb;
    client->timer_user_data = user_data;
    client->timer_interval_ms = interval_ms;

    lws_sul_schedule(client->context, 0, &client->sul_timer,
                     on_sample_timer, (lws_usec_t)interval_ms * LWS_US_PER_MS);
    return 0;
}

void wsclient_set_connection_cb(wsclient_t *client, wsclient_conn_cb cb, void *user_data) {
    if (!client) return;
    client->conn_cb = cb;
    client->conn_user_data = user_data;
}

int wsclient_service(wsclient_t *client, int timeout_ms) {
    if (!client || !client->context) return -1;
    (void)timeout_ms;
    lws_service(client->context, 0);
    return client->connected;
}

int wsclient_send(wsclient_t *client, const char *data, size_t len) {
    if (!client || !client->connected || !client->wsi) return -1;

    if (client->queue_count >= MAX_QUEUE_DEPTH) {
        msg_queue_item_t *old = client->queue_head;
        client->queue_head = old->next;
        if (!client->queue_head) client->queue_tail = NULL;
        free(old->buf);
        free(old);
        client->queue_count--;
    }

    msg_queue_item_t *item = malloc(sizeof(msg_queue_item_t));
    if (!item) return -1;

    item->buf = malloc(LWS_PRE + len);
    if (!item->buf) {
        free(item);
        return -1;
    }
    memcpy(item->buf + LWS_PRE, data, len);
    item->len = len;
    item->next = NULL;

    if (client->queue_tail) {
        client->queue_tail->next = item;
        client->queue_tail = item;
    } else {
        client->queue_head = item;
        client->queue_tail = item;
    }
    client->queue_count++;

    lws_callback_on_writable(client->wsi);
    return 0;
}

int wsclient_is_connected(wsclient_t *client) {
    return client && client->connected;
}

void wsclient_wake(wsclient_t *client) {
    if (client && client->context) {
        lws_cancel_service(client->context);
    }
}

void wsclient_destroy(wsclient_t *client) {
    if (!client) return;

    if (client->context) {
        lws_sul_cancel(&client->sul_timer);
        lws_sul_cancel(&client->sul_reconnect);
    }

    clear_queue(client);

    if (client->context) {
        lws_context_destroy(client->context);
    }
    free(client);
}