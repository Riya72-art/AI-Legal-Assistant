/* C Program: Basic System Calls Demonstration */
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>

int main() {
    int fd;
    char buffer[50];

    fd = open("sample.txt", O_CREAT | O_RDWR, 0644);

    if (fd == -1) {
        printf("Error opening file\n");
        return 1;
    }

    write(fd, "Hello Linux System Calls\n", 25);

    lseek(fd, 0, SEEK_SET);

    read(fd, buffer, 25);
    buffer[25] = '\0';

    printf("File Content: %s", buffer);
    printf("Process ID: %d\n", getpid());
    printf("User ID: %d\n", getuid());
    printf("Group ID: %d\n", getgid());

    close(fd);

    return 0;
}