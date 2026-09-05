#include "daemon.h"

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

static void write_pidfile(const char *pidfile) {
    if (!pidfile || pidfile[0] == '\0') return;

    FILE *f = fopen(pidfile, "w");
    if (!f) return;

    fprintf(f, "%d\n", getpid());
    fclose(f);
}

int daemonize(const char *pidfile, const char *log_file) {
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (pid > 0) _exit(0);

    if (setsid() < 0) return -1;

    pid = fork();
    if (pid < 0) return -1;
    if (pid > 0) _exit(0);

    umask(0027);
    if (chdir("/") != 0) return -1;

    int devnull = open("/dev/null", O_RDWR);
    if (devnull >= 0) {
        dup2(devnull, STDIN_FILENO);
    }

    int out_fd = -1;
    if (log_file && log_file[0] != '\0') {
        out_fd = open(log_file, O_WRONLY | O_CREAT | O_APPEND, 0640);
    }
    if (out_fd < 0) {
        out_fd = devnull;
    }

    if (out_fd >= 0) {
        dup2(out_fd, STDOUT_FILENO);
        dup2(out_fd, STDERR_FILENO);
    }

    if (devnull >= 0 && devnull > STDERR_FILENO) close(devnull);
    if (out_fd >= 0 && out_fd > STDERR_FILENO && out_fd != devnull) close(out_fd);

    write_pidfile(pidfile);
    return 0;
}