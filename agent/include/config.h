#ifndef LYNCEUS_CONFIG_H
#define LYNCEUS_CONFIG_H

typedef struct {
    char host[256];
    int port;
    char server_id[128];
    char key[256];
    int interval_sec;
    int use_tls;
    int insecure_tls;
    int daemonize;
    char pidfile[256];
    char log_file[256];
} agent_config_t;

void config_set_defaults(agent_config_t *cfg);
int config_load_file(agent_config_t *cfg, const char *path);

#endif