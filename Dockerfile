# WARNING! This is not in any way production ready. It is just for testing!

FROM opensuse/leap:15

ENV container docker

WORKDIR /test_dir
COPY . /test_dir

VOLUME [ "/sys/fs/cgroup" ]

RUN ["/bin/bash", "-c", "tests/setup-test-docker.sh"]

# Set this as an entrypoint
CMD ["/usr/lib/systemd/systemd", "--system"]
