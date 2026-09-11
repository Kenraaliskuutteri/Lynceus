#ifndef LYNCEUS_WSCLIENT_H
#define LYNCEUS_WSCLIENT_H

#include <stddef.h>

typedef struct wsclient wsclient_t;
typedef void (*wsclient_timer_cb)(wsclient_t *client, void *user_data);
typedef void (*wsclient_conn_cb)(wsclient_t *client, int connected, void *user_data);

wsclient_t *wsclient_create(const char *host, int port, const char *path, int use_tls, int insecure_tls);
int wsclient_service(wsclient_t *client, int timeout_ms);
int wsclient_send(wsclient_t *client, const char *data, size_t len);
int wsclient_is_connected(wsclient_t *client);
int wsclient_set_periodic_timer(wsclient_t *client, int interval_ms, wsclient_timer_cb cb, void *user_data);
void wsclient_set_connection_cb(wsclient_t *client, wsclient_conn_cb cb, void *user_data);
void wsclient_wake(wsclient_t *client);
void wsclient_destroy(wsclient_t *client);

#endif