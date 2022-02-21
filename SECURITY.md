# Security Policy

## Supported Versions

| Version   | Supported                |
| --------- | ------------------------ |
| 4.0.X     | Next API breaking Release |
| 3.3.x     | Current Version: 3.3.2   |
| 3.2.x     | Security only            |
| 3.1.x     | EOL                      |
| 3.0.x     | EOL                      |
| 2.8.x     | EOL                      |
| 2.6.x     | EOL                      |
| 2.4.x     | EOL                      |
| 2.2.x     | EOL                      |
| < 2.x.x   | EOL                      |

Due to the amount of maintainers we have, we can only support the most current version. Old versions won't be actively
maintained.

## Reporting a Vulnerability

If you find a security vulnerability we would love if you could report this to
[cobbler.project@gmail.com](mailto:cobbler.project@gmail.com). This address is under control of @SchoolGuy currently.

Please be aware that since this project is not professionally managed we may have a hard time fixing this by ourselves.
The more details we get, the more likely it is that we can react to it properly.

Since there is no funding for Cobbler, we can't offer you anything but our deepest thanks for finding a security issue.

## Known problems

All open security problems which are publicly known are to be found at:

> https://github.com/cobbler/cobbler/issues?q=is%3Aissue+is%3Aopen+label%3Asecurity

## Remarks

We don't offer a SELinux profile or an Apparmor profile. Also this tool manages your
DHCP and TFTP server. This implicates that Cobbler has a lot of control of your network, thus we would advise you to
protect it as much as possible. However please be aware of the implications when using it. There is code in there to
automatically download and update files on your local filesystem as well as serving files like bootloaders which have
the potential (if compromised) to do a lot of harm.
