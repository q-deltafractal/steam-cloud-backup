# jetCDNparse

micro-script for downloading all save files from [steam cloud](https://store.steampowered.com/account/remotestorage)


## backup process

### requirements

- [ ] [uv](https://docs.astral.sh/uv/) python package manager
- [ ] [git](https://git-scm.com/install/) version control

_latest versions_

### preparation

```bash
# clone repo
git clone https://github.com/q-deltafractal/steam-cloud-backup.git
cd steam-cloud-backup
```

```bash
# setup virtual env
uv sync
```

### backup

```console
$ uv run main.py
INFO:__main__:iter game: Steam Client; files count: 2
...
```

<br>

## usage

```console
$ uv run main.py -h
usage: steam-cloud-backup [-h] [-i SESSIONID] [-l STEAMLOGINSECURE] [-j MAX_CONCURRENT_CONNECTIONS] [--connect-timeout CONNECT_TIMEOUT] [--useragent USERAGENT] folder

micro-script for downloading all save files from steam cloud

positional arguments:
  folder

options:
  -h, --help            show this help message and exit
  -i, --sessionId SESSIONID
  -l, --steamLoginSecure STEAMLOGINSECURE
  -j, --max-concurrent-connections MAX_CONCURRENT_CONNECTIONS
  --connect-timeout CONNECT_TIMEOUT
  --useragent USERAGENT
```

<br>

## license

project is licensed under:

<table>
  <tr>
    <td>
      MIT
    </td>
    <td>
      <a href="LICENSE">LICENSE</a>
    </td>
    <td>
      https://mit-license.org/
    </td>
  </tr>
</table>
