#ifndef LYNCEUS_WSCLIENT_H
#define LYNCEUS_WSCLIENT_H

#include <stddef.h>

typedef struct wsclient wsclient_t;

wsclient_t *wsclient_create(const char *host, int port, const char *path, int use_tls, int insecure_tls);
int wsclient_service(wsclient_t *client, int timeout_ms);
int wsclient_send(wsclient_t *client, const char *data, size_t len);
int wsclient_is_connected(wsclient_t *client);
void wsclient_destroy(wsclient_t *client);

#endif