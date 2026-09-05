#include "config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

void config_set_defaults(agent_config_t *cfg) {
    memset(cfg, 0, sizeof(*cfg));
    cfg->port = 8000;
    cfg->interval_sec = 2;
    snprintf(cfg->pidfile, sizeof(cfg->pidfile), "%s", "/run/lynceus-agent.pid");
}

static char *trim(char *s) {
    while (isspace((unsigned char)*s)) s++;
    if (*s == '\0') return s;

    char *end = s + strlen(s) - 1;
    while (end > s && isspace((unsigned char)*end)) *end-- = '\0';
    return s;
}

int config_load_file(agent_config_t *cfg, const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return -1;

    char line[512];
    while (fgets(line, sizeof(line), f)) {
        char *trimmed = trim(line);
        if (trimmed[0] == '\0' || trimmed[0] == '#') continue;

        char *eq = strchr(trimmed, '=');
        if (!eq) continue;
        *eq = '\0';

        char *key = trim(trimmed);
        char *value = trim(eq + 1);

        if (strcmp(key, "host") == 0) {
            snprintf(cfg->host, sizeof(cfg->host), "%s", value);
        } else if (strcmp(key, "port") == 0) {
            cfg->port = atoi(value);
        } else if (strcmp(key, "id") == 0) {
            snprintf(cfg->server_id, sizeof(cfg->server_id), "%s", value);
        } else if (strcmp(key, "key") == 0) {
            snprintf(cfg->key, sizeof(cfg->key), "%s", value);
        } else if (strcmp(key, "interval") == 0) {
            cfg->interval_sec = atoi(value);
        } else if (strcmp(key, "tls") == 0) {
            cfg->use_tls = (strcmp(value, "true") == 0 || strcmp(value, "1") == 0);
        } else if (strcmp(key, "insecure") == 0) {
            cfg->insecure_tls = (strcmp(value, "true") == 0 || strcmp(value, "1") == 0);
        } else if (strcmp(key, "pidfile") == 0) {
            snprintf(cfg->pidfile, sizeof(cfg->pidfile), "%s", value);
        } else if (strcmp(key, "log_file") == 0) {
            snprintf(cfg->log_file, sizeof(cfg->log_file), "%s", value);
        }
    }

    fclose(f);
    return 0;
}